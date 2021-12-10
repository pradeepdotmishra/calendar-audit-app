from datetime import datetime
import os
import flask
import requests
import operation
import json
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/calendar']

app = flask.Flask(__name__)

app.secret_key = 'GoogleCalendarAudit-1.0'

@app.route('/')
def index():
    return flask.render_template('index.html')

@app.route('/metrics')
def metrics():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
    calendar = googleapiclient.discovery.build('calendar', 'v3', credentials=credentials)

    calendar_list  = calendar.calendarList().list(minAccessRole='owner').execute()
    id=calendar_list['items'][0]['id']

    allEvents= calendar.events().list(calendarId=id,singleEvents=True,orderBy='startTime').execute()
    now=datetime.utcnow().isoformat() + 'Z'
    beforeEvents= calendar.events().list(calendarId=id,timeMax=now,singleEvents=True,orderBy='startTime').execute()
    
    topThreePersion = json.dumps(operation.getTopThreePerson(allEvents,id))
    timeSpentConductInterview = operation.getTimeSpentConductInterview(beforeEvents,id)
    monthWithHighestMeet = operation.getMonthWithHighestMeet(beforeEvents)
    timeSpentThreeMonth = json.dumps(operation.getTimeSpentThreeMonth(beforeEvents))
    

    flask.session['credentials'] = operation.credentials_to_dict(credentials)
    #return json.dumps(timeSpentThreeMonth)
    return flask.render_template('metrics.html',
    topThreeID=topThreePersion,
    timeInInterview=timeSpentConductInterview,
    monthWithHighestMeet=monthWithHighestMeet,
    timeSpentThreeMonth=timeSpentThreeMonth)

@app.route('/authorize')
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)

  # The URI created here must exactly match one of the authorized redirect URIs
  # for the OAuth 2.0 client, which you configured in the API Console. If this
  # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
  # error.
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
      # Enable offline access so that you can refresh an access token without
      # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
      # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

  # Store the state so the callback can verify the auth server response.
    flask.session['state'] = state

    return flask.redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
  # Specify the state when creating the flow in the callback so that it can
  # verified in the authorization server response.
    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

  # Store credentials in the session.
  # ACTION ITEM: In a production app, you likely want to save these
  #              credentials in a persistent database instead.
    credentials = flow.credentials
    flask.session['credentials'] = operation.credentials_to_dict(credentials)

    return flask.redirect(flask.url_for('metrics'))

@app.route('/revoke')
def revoke():
    if 'credentials' not in flask.session:
        return ('You need to <a href="/authorize">authorize</a> before ' + 'testing the code to revoke credentials.')

    credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])

    revoke = requests.post('https://oauth2.googleapis.com/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

    status_code = getattr(revoke, 'status_code')
    if status_code == 200:
        return('Credentials successfully revoked.' + flask.render_template('index.html'))
    else:
        return('An error occurred.' + flask.render_template('index.html'))

@app.route('/clear')
def clear_credentials():
    if 'credentials' in flask.session:
        del flask.session['credentials']
    return ('Credentials have been cleared.<br><br>' + flask.render_template('index.html'))



if __name__ == "__main__":
    # When running locally, disable OAuthlib's HTTPs verification.
    # ACTION ITEM for developers:
    #     When running in production *do not* leave this option enabled.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    # Specify a hostname and port that are set as a valid redirect URI
    # for your API project in the Google API Console.
    app.run(debug=True)    