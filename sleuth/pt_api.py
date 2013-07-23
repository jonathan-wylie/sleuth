from lxml import objectify
import subprocess


URL_API3 = 'https://www.pivotaltracker.com/services/v3'
BLOCKS = ['current', 'icebox', 'backlog', 'done']
SINGLE_BLOCKS = ['current', 'icebox']


class PT_APIException(Exception):
    pass


def APICall(url, token):
    child = subprocess.Popen("curl -H 'X-TrackerToken: %s' -X GET %s" % (token, url), shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdoutdata, _) = child.communicate()
            
    return stdoutdata


def getStories(project_id, block, token, story_constructor=lambda project_id, storyxml: storyxml):
    ''' Return the stories for all the stories in the block eg current,
        for project with ID project_id
    '''
    if block not in BLOCKS:
        raise ValueError("The block value must be in %s, not %s" % (BLOCKS, block))
    stories = []
    
    url = '%s/projects/%s/iterations/%s' % (URL_API3, project_id, block)
        
    data = APICall(url, token)
#     if block == 'current':
#         print data
    iterations = objectify.fromstring(data)
    
    for iteration in iterations.iterchildren():
        stories.append([story_constructor(project_id, storyxml) for storyxml in iteration.stories.iterchildren()])
    
    if block in SINGLE_BLOCKS:
        #print data
        return stories[0]
    else:
        return stories
