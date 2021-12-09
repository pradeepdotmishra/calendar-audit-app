from datetime import datetime
from dateutil import parser
from dateutil.relativedelta import relativedelta
import os
import calendar
import flask
import requests
import json
import collections
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
    afterEvents= calendar.events().list(calendarId=id,timeMin=now,singleEvents=True,orderBy='startTime').execute()
    beforeEvents= calendar.events().list(calendarId=id,timeMax=now,singleEvents=True,orderBy='startTime').execute()
    
    topThreePersion = json.dumps(getTopThreePerson(allEvents,id))
    timeSpentConductInterview = getTimeSpentConductInterview(beforeEvents,id)
    monthWithHighestMeet = getMonthWithHighestMeet(beforeEvents)
    timeSpentThreeMonth = json.dumps(getTimeSpentThreeMonth(beforeEvents))
    

    flask.session['credentials'] = credentials_to_dict(credentials)
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
    flask.session['credentials'] = credentials_to_dict(credentials)

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

def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}

def getTimeSpentThreeMonth(beforeEvents):
    monthDict = {}
    meetings = beforeEvents['items']
    meetings.reverse()
    end_date = datetime.utcnow().date().replace(day=1)
    starting_date = end_date - relativedelta(months=3)

    for meeting in meetings:
        startTime=parser.parse(meeting['start']['dateTime'])
        if startTime.date() >= starting_date and startTime.date() < end_date:
            meetingMonth = calendar.month_name[startTime.month]
            endTime= parser.parse(meeting['end']['dateTime'])
            timeDifference= endTime-startTime
            timeSpent=timeDifference.total_seconds()
            if meetingMonth in monthDict.keys():
                monthDict[meetingMonth]= monthDict[meetingMonth]+timeSpent
            else:
                monthDict[meetingMonth]=timeSpent
    for month,timeSpent in monthDict.items():
        hour = divmod(timeSpent, 3600)
        minutes = divmod(hour[1], 60)
        monthDict[month] = str(hour[0]) + " hours, " +str(minutes[0]) + " minutes"
    return monthDict

def getMonthWithHighestMeet(beforeEvents):
    monthDict = {}
    meetings = beforeEvents['items']
    for meeting in meetings:
        startTime=parser.parse(meeting['start']['dateTime'])
        meetingMonth=startTime.month
        if meetingMonth in monthDict.keys():
            monthDict[meetingMonth]= monthDict[meetingMonth]+1
        else:
            monthDict[meetingMonth]=1
    sortedMonth = sorted(monthDict.items(), key=lambda x: x[1],reverse=True)
    return calendar.month_name[sortedMonth[0][0]]

def getTimeSpentConductInterview(beforeEvents,id):
    meetings = beforeEvents['items']
    timeSpent=0
    for meeting in meetings:
        if meeting['organizer']['email'] == id and "interview" in meeting['summary'].lower():
            
            startTime=parser.parse(meeting['start']['dateTime'])
            endTime= parser.parse(meeting['end']['dateTime'])
            timeDifference= endTime-startTime
            timeSpent+=timeDifference.total_seconds()
    hour = divmod(timeSpent, 3600)
    minutes = divmod(hour[1], 60)

    return str(hour[0]) + " hours, " +str(minutes[0]) + " minutes"

def getTopThreePerson(events,id):
    emailDict = {}
    result=['']*3
    meetings = events['items']
    for meeting in meetings:
        if "attendees" in meeting:
            users = meeting['attendees']
            for attendee in users:
                userEmailId= attendee['email']
                if userEmailId in emailDict.keys():
                    emailDict[userEmailId]= emailDict[userEmailId]+1
                else:
                    emailDict[userEmailId]=1
    emailDict.pop(id)
    sorted_email = sorted(emailDict.items(), key=lambda x: x[1],reverse=True)

    for i in range(3):
        result[i]= sorted_email[i]

    return collections.OrderedDict(result)


if __name__ == "__main__":
    # When running locally, disable OAuthlib's HTTPs verification.
    # ACTION ITEM for developers:
    #     When running in production *do not* leave this option enabled.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    # Specify a hostname and port that are set as a valid redirect URI
    # for your API project in the Google API Console.
    app.run(debug=True)    