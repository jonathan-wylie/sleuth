from lxml import objectify
import subprocess


URL_API3 = 'https://www.pivotaltracker.com/services/v3'
SINGLE_BLOCK = ['current', 'icebox']


def APICall(url, token):
    child = subprocess.Popen("curl -H 'X-TrackerToken: %s' -X GET %s" % (token, url), shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdoutdata, _) = child.communicate()
            
    return stdoutdata


def getStories(project_id, block, token, story_constructor=lambda project_id,storyxml: storyxml):
    ''' Return the stories for all the stories in the block eg current, 
        for project with ID project_id
    '''
    stories = []
    
    url = '%s/projects/%s/iterations/%s' % (URL_API3, project_id, block)
        
    data = APICall(url, token)
    
    iterations = objectify.fromstring(data)
    
    if block in ['backlog', 'done']:
        for iteration in iterations.iterchildren():
            stories.append([story_constructor(project_id, storyxml) for storyxml in iteration.stories.iterchildren()])
    elif block in ['current', 'icebox']:
        stories = [story_constructor(project_id, storyxml) for storyxml in iterations.iteration.stories.iterchildren()]
    
    return stories


