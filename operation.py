from datetime import datetime
from dateutil import parser
from dateutil.relativedelta import relativedelta
import calendar
import collections

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
        if "attendees" in meeting and len(meeting['attendees']) > 1:
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
        if "attendees" in meeting and len(meeting['attendees']) > 1:
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
        if meeting['organizer']['email'] == id and "interview" in meeting['summary'].lower() and "attendees" in meeting and len(meeting['attendees']) > 1:
            
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
