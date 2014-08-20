import lxml
import logging
import subprocess
import urllib
import time
import requests

from lxml import objectify as lxml_objectify

logger = logging.getLogger(__name__)

URL_API3 = 'https://www.pivotaltracker.com/services/v3'
URL_API4 = 'https://www.pivotaltracker.com/services/v4'
BLOCKS = ['current', 'icebox', 'backlog', 'done']


class PT_APIException(Exception):
    pass


def APICall(url, token):
    # cmd = "curl -H 'X-TrackerToken: %s' -X GET %s"
    # child = subprocess.Popen(cmd % (token, url),
    #                          shell=True, stderr=subprocess.PIPE,
    #                          stdout=subprocess.PIPE)
    # (stdoutdata, _) = child.communicate()
    return requests.get(url, headers={'X-TrackerToken': token}).text


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
        story_filter = urllib.urlencode({'filter': self.story_filter})
        return '%s/projects/%s/stories?%s' % (URL_API3, self.project_id,
                                              story_filter)

    def get(self, token):
        ''' Actually get the stories
        '''
        data = APICall(self.url, token)
        return data


def get_stories(project_id, block, token, story_constructor=lambda project_id,
                storyxml: storyxml):
    ''' Return the stories for all the stories in the block eg current,
        for project with ID project_id
    '''
    if block not in BLOCKS:
        value_error_tmpl = 'The block value must be in %s, not %s'
        raise ValueError(value_error_tmpl % (BLOCKS, block))

    stories = []
    if block == 'icebox':
        # icebox stories are 'unscheduled', can't query directly for icebox
        # stories, like we can with the other blocks
        story_search = StorySearch(project_id).filter_by_states(['unscheduled'])
        data = story_search.get(token)
        storiesxml = objectify(data)
        if storiesxml is not None:
            stories.append([story_constructor(project_id, storyxml)
                            for storyxml
                            in storiesxml.iterchildren()])
    else:
        if block == "done":
            url_tmpl = '%s/projects/%s/iterations/%s?offset=-6'
            url = url_tmpl % (URL_API3, project_id, block)
        else:
            url = '%s/projects/%s/iterations/%s' % (URL_API3, project_id, block)
        data = APICall(url, token)
        iterations = objectify(data)
        try:
            for iteration in iterations.iterchildren():
                try:
                    stories.append([story_constructor(project_id, storyxml)
                                    for storyxml
                                    in iteration.stories.iterchildren()])
                except:
                    logger.exception("Problem loading stories from iteration")
        except Exception:
            logger.exception(dir(iterations))

    return stories


def get_project_activities(project_id, since, token):
    # 2010/3/15%0000:00:00%20PST
    since = "%s%s%s%s%s%s%s" % (since.strftime('%Y/'),
                                str(since.month),
                                since.strftime('/%d'),
                                '%00',
                                since.strftime('%H:%M:%S'),
                                '%20',
                                time.tzname[0])
    url_tmpl = '%s/projects/%s/activities?occurred_since_date=%s'
    data = APICall(url_tmpl % (URL_API4, project_id, since), token)
    activitiesxml = objectify(data)
    return activitiesxml


def get_project_activities_v3(project_id, since, token):
    # 2010/3/15%0000:00:00%20PST
    since = "%s%s%s%s%s%s%s" % (since.strftime('%Y/'),
                                str(since.month),
                                since.strftime('/%d'),
                                '%00',
                                since.strftime('%H:%M:%S'),
                                '%20',
                                time.tzname[0])
    url_tmpl = '%s/projects/%s/activities?occurred_since_date=%s'
    data = APICall(url_tmpl % (URL_API3, project_id, since), token)
    activitiesxml = objectify(data)
    return activitiesxml


def objectify(some_xml):
    ''' Safely objectify the xml
    '''
    try:
        return lxml_objectify.fromstring(some_xml.replace(' encoding="UTF-8"', ""))
    except Exception:
        logger.exception("Problem objectifying the xml \n %s" % some_xml)
        import sys
        sys.exit(1)
        return None


def to_str(objectified_object):
    return lxml.etree.tostring(objectified_object)
