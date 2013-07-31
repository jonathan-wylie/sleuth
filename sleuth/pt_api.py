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
    
    def __init__(self, projectID, storyFilter=None):
        self.projectID = projectID
        self.storyFilter = storyFilter
    
    def filterByID(self, storyID):
        """ Filter the stories by the story id
        """
        if self.storyFilter is not None:
            storyFilter = self.storyFilter + " id: %s" % storyID
        else:
            storyFilter = "id: %s" % storyID
        
        return StorySearch(self.projectID, storyFilter=storyFilter)

    def filterByIDs(self, storyIDs):
        """ Filter the stories by the story id
        """
        if self.storyFilter is not None:
            storyFilter = self.storyFilter + " id: %s" % ",".join(storyIDs)
        else:
            storyFilter = " id: %s" % ",".join(storyIDs)
        
        return StorySearch(self.projectID, storyFilter=storyFilter)
    
    def filterByRequester(self, requester):
        """ Filter the stories by requester
        
        """
        if self.storyFilter is not None:
            storyFilter = self.storyFilter + " requester: %s" % requester
        else:
            storyFilter = "requester: %s" % requester
        
        return StorySearch(self.projectID, storyFilter=storyFilter)

    def filterIncludeDone(self):
        """ Include stories completed in previous iterations
        """
        if self.storyFilter is not None:
            storyFilter = self.storyFilter + " includedone:true"
        else:
            storyFilter = "includedone:true"
        
        return StorySearch(self.projectID, storyFilter=storyFilter)
    
    def filterByModifiedDate(self, modifiedDate):
        """ Include stories modified since modifiedDate
        """
        filterDate = str(modifiedDate)
        if self.storyFilter is not None:
            storyFilter = self.storyFilter + '  modified_since:"%s"' % filterDate
        else:
            storyFilter = "modified_since:%s" % filterDate
        
        return StorySearch(self.projectID, storyFilter=storyFilter)

    def filterByStates(self, states):
        """ Include only stories in this state
        """
        if self.storyFilter is not None:
            storyFilter = self.storyFilter + "  state:%s" % ",".join(states)
        else:
            storyFilter = "state:%s" % ",".join(states)
        
        return StorySearch(self.projectID, storyFilter=storyFilter)
    
    def filterByLabel(self, label):
        if self.storyFilter is not None:
            storyFilter = self.storyFilter + "  label:%s" % label
        else:
            storyFilter = "label:%s" % label
        
        return StorySearch(self.projectID, storyFilter=storyFilter)

    def filterByType(self, storyType):
        if self.storyFilter is not None:
            storyFilter = self.storyFilter + "  type:%s" % storyType
        else:
            storyFilter = "type:%s" % storyType
        
        return StorySearch(self.projectID, storyFilter=storyFilter)
    
    @property
    def url(self):
        """ Return the url to make the api call
        """
        return "%s/projects/%s/stories?%s" % (URL_API3, self.projectID, urllib.urlencode({"filter": self.storyFilter}))
        
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
