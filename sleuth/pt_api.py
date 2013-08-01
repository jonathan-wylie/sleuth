from lxml import objectify
import logging
import subprocess
import urllib

logger = logging.getLogger(__name__)

URL_API3 = 'https://www.pivotaltracker.com/services/v3'
BLOCKS = ['current', 'icebox', 'backlog', 'done']


class PT_APIException(Exception):
    pass


def APICall(url, token):
    child = subprocess.Popen("curl -H 'X-TrackerToken: %s' -X GET %s" % (token, url), shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdoutdata, _) = child.communicate()
            
    return stdoutdata


class StorySearch():
    
    def __init__(self, project_id, story_filter=None):
        self.project_id = project_id
        self.story_filter = story_filter
    
    def filterByID(self, storyID):
        """ Filter the stories by the story id
        """
        if self.story_filter is not None:
            story_filter = self.story_filter + " id: %s" % storyID
        else:
            story_filter = "id: %s" % storyID
        
        return StorySearch(self.project_id, story_filter=story_filter)

    def filterByIDs(self, storyIDs):
        """ Filter the stories by the story id
        """
        if self.story_filter is not None:
            story_filter = self.story_filter + " id: %s" % ",".join(storyIDs)
        else:
            story_filter = " id: %s" % ",".join(storyIDs)
        
        return StorySearch(self.project_id, story_filter=story_filter)
    
    def filterByRequester(self, requester):
        """ Filter the stories by requester
        
        """
        if self.story_filter is not None:
            story_filter = self.story_filter + " requester: %s" % requester
        else:
            story_filter = "requester: %s" % requester
        
        return StorySearch(self.project_id, story_filter=story_filter)

    def filterIncludeDone(self):
        """ Include stories completed in previous iterations
        """
        if self.story_filter is not None:
            story_filter = self.story_filter + " includedone:true"
        else:
            story_filter = "includedone:true"
        
        return StorySearch(self.project_id, story_filter=story_filter)
    
    def filterByModifiedDate(self, modifiedDate):
        """ Include stories modified since modifiedDate
        """
        filterDate = str(modifiedDate)
        if self.story_filter is not None:
            story_filter = self.story_filter + '  modified_since:"%s"' % filterDate
        else:
            story_filter = "modified_since:%s" % filterDate
        
        return StorySearch(self.project_id, story_filter=story_filter)

    def filterByStates(self, states):
        """ Include only stories in this state
        """
        if self.story_filter is not None:
            story_filter = self.story_filter + "  state:%s" % ",".join(states)
        else:
            story_filter = "state:%s" % ",".join(states)
        
        return StorySearch(self.project_id, story_filter=story_filter)
    
    def filterByLabel(self, label):
        if self.story_filter is not None:
            story_filter = self.story_filter + "  label:%s" % label
        else:
            story_filter = "label:%s" % label
        
        return StorySearch(self.project_id, story_filter=story_filter)

    def filterByType(self, storyType):
        if self.story_filter is not None:
            story_filter = self.story_filter + "  type:%s" % storyType
        else:
            story_filter = "type:%s" % storyType
        
        return StorySearch(self.project_id, story_filter=story_filter)
    
    @property
    def url(self):
        """ Return the url to make the api call
        """
        return "%s/projects/%s/stories?%s" % (URL_API3, self.project_id, urllib.urlencode({"filter": self.story_filter}))
        
    def get(self, token):
        """ Actually get the stories
        """
        data = APICall(self.url, token)
        return data


def getStories(project_id, block, token, story_constructor=lambda project_id, storyxml: storyxml):
    ''' Return the stories for all the stories in the block eg current,
        for project with ID project_id
    '''
    if block not in BLOCKS:
        raise ValueError("The block value must be in %s, not %s" % (BLOCKS, block))
    
    stories = []
    if block == 'icebox':
        # icebox stories are "unscheduled", can't query directly for icebox stories, like we can with the other blocks
        data = StorySearch(project_id).filterByStates(["unscheduled"]).get(token)
        storiesxml = objectify.fromstring(data)
        stories.append([story_constructor(project_id, storyxml) for storyxml in storiesxml.iterchildren()])
    else:
        url = '%s/projects/%s/iterations/%s' % (URL_API3, project_id, block)
        data = APICall(url, token)
        iterations = objectify.fromstring(data)
        for iteration in iterations.iterchildren():
            stories.append([story_constructor(project_id, storyxml) for storyxml in iteration.stories.iterchildren()])
        
    return stories
