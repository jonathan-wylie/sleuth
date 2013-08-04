from lxml import objectify
import logging
import subprocess
import urllib
import time

logger = logging.getLogger(__name__)

URL_API3 = 'https://www.pivotaltracker.com/services/v3'
URL_API4 = 'https://www.pivotaltracker.com/services/v4'
BLOCKS = ['current', 'icebox', 'backlog', 'done']


class PT_APIException(Exception):
    pass


def APICall(url, token):
    child = subprocess.Popen("curl -H 'X-TrackerToken: %s' -X GET %s" % (token, url),
                             shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdoutdata, _) = child.communicate()
    return stdoutdata


class StorySearch():
    
    def __init__(self, project_id, story_filter=None):
        self.project_id = project_id
        self.story_filter = story_filter
    
    def filter_by_states(self, states):
        ''' Include only stories in this state
        '''
        states = ','.join(states)
        if self.story_filter is not None:
            story_filter = self.story_filter + ' state:%s' % states
        else:
            story_filter = 'state:%s' % states
        
        return StorySearch(self.project_id, story_filter=story_filter)
    
    @property
    def url(self):
        ''' Return the url to make the api call
        '''
        return '%s/projects/%s/stories?%s' % (URL_API3, self.project_id, urllib.urlencode({'filter': self.story_filter}))
        
    def get(self, token):
        ''' Actually get the stories
        '''
        data = APICall(self.url, token)
        return data


def get_stories(project_id, block, token, story_constructor=lambda project_id, storyxml: storyxml):
    ''' Return the stories for all the stories in the block eg current,
        for project with ID project_id
    '''
    if block not in BLOCKS:
        raise ValueError('The block value must be in %s, not %s' % (BLOCKS, block))
    
    stories = []
    if block == 'icebox':
        # icebox stories are 'unscheduled', can't query directly for icebox stories, like we can with the other blocks
        data = StorySearch(project_id).filter_by_states(['unscheduled']).get(token)
        storiesxml = objectify.fromstring(data)
        stories.append([story_constructor(project_id, storyxml) for storyxml in storiesxml.iterchildren()])
    else:
        url = '%s/projects/%s/iterations/%s' % (URL_API3, project_id, block)
        data = APICall(url, token)
        iterations = objectify.fromstring(data)
        for iteration in iterations.iterchildren():
            stories.append([story_constructor(project_id, storyxml) for storyxml in iteration.stories.iterchildren()])
        
    return stories


def get_project_activities(project_id, since, token):
    # 2010/3/15%0000:00:00%20PST
    since = since.strftime('%Y/') +str(since.month) + since.strftime('/%d') + '%00' + since.strftime('%H:%M:%S') + '%20' + time.tzname[0]
    data = APICall('%s/projects/%s/activities?occurred_since_date=%s' % (URL_API4, project_id, since),
                   token)
    #print data
    activitiesxml = objectify.fromstring(data)
    return activitiesxml


def get_project_activities_v3(project_id, since, token):
    # 2010/3/15%0000:00:00%20PST
    since = since.strftime('%Y/') +str(since.month) + since.strftime('/%d') + '%00' + since.strftime('%H:%M:%S') + '%20' + time.tzname[0]
    data = APICall('%s/projects/%s/activities?occurred_since_date=%s' % (URL_API3, project_id, since),
                   token)
    activitiesxml = objectify.fromstring(data)
    return activitiesxml
