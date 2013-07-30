from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from lxml import objectify
import pt_api


class Sleuth_Web_App(object):
    '''This class listens for pivotal tracker activity posts, and publishes them.'''
    
    def __init__(self, activity_receiver, port=8081):
        self.__activity_receiver = activity_receiver
        self.__port = port
        self.__config = Configurator()
        self.__config.add_route('activity_web_hook', '/activity_web_hook')
        self.__config.add_view(self.__activity_web_hook, route_name='activity_web_hook', request_method='POST')
        self.__app = self.__config.make_wsgi_app()
        self.__server = make_server('0.0.0.0', self.__port, self.__app)
        self.__server.serve_forever()
    
    def __activity_web_hook(self, request):
        print request.body
        activity = objectify.fromstring(request.body)
        self.__activity_receiver.activity_web_hook(activity)
        return Response('OK')


class Story(object):
    '''The class represents a Pivotal Tracker User Story'''

    @staticmethod
    def create(project_id, storyxml):
        try:
            labels = str(storyxml.labels).split(',')
        except AttributeError:
            labels = []
        try:
            accepted_at = storyxml.accepted_at
        except AttributeError:
            accepted_at = None
        try:
            owned_by = storyxml.owned_by
        except AttributeError:
            owned_by = None
        try:
            estimate = storyxml.estimate
        except AttributeError:
            estimate = None
        try:
            description = storyxml.description
        except AttributeError:
            description = None
        try:
            created_at = storyxml.created_at
        except AttributeError:
            created_at = None
        return Story(storyxml.id, project_id,
                    storyxml.story_type, storyxml.url, estimate, storyxml.current_state,
                    description, storyxml.name, storyxml.requested_by, owned_by,
                    created_at=created_at, accepted_at=accepted_at, labels=labels)
       
    def __init__(self, story_id, project_id, story_type, url, estimate, current_state, description, name, requested_by, owned_by,
                 created_at=None, accepted_at=None, labels=[]):
        self.id = story_id
        self.project_id = project_id
        self.story_type = story_type
        self.url = url
        self.estimate = estimate
        self.current_state = current_state
        self.description = description
        self.name = name
        self.requested_by = requested_by
        self.owned_by = owned_by
        self.created_at = created_at
        self.accepted_at = accepted_at
        self.labels = labels
    
    def update(self, activity, storyxml):
        
        for attribute in ["accepted_at", "owned_by", "estimate", "description", "created_at", "story_type",
                          "url", "estimate", "current_state", "description", "name", "requested_by", "owned_by",
                          "created_at", "accepted_at"]:
            if hasattr(storyxml, attribute):
                newValue = getattr(storyxml, attribute)
                oldValue = getattr(self, attribute)
                print "%s changed from %s to %s" % (attribute, newValue, oldValue)
                setattr(self, attribute, newValue)
        
        try:
            labels = str(storyxml.labels).split(',')
            print "labels changed from %s to %s" % (self.labels, labels)
            self.labels = labels
        except AttributeError:
            labels = []
        
        try:
            project_id = activity.project_id
            print "project_id changed from %s to %s" % (self.project_id, project_id)
            self.project_id = project_id
        except AttributeError:
            project_id = None

    def delete(self):
        pass


def _flatten_list(alist):
    if type(alist) != type([]):
        return [alist]
    return_list = []
    for item in alist:
        return_list.extend(_flatten_list(item))
    return return_list


class Sleuth(object):
    '''This class receives the activity xml parsed from the web app, and updates all the data'''
    def __init__(self, project_ids, track_blocks, token):
        self.project_ids = project_ids
        self.token = token
        self.track_blocks = track_blocks
        self.stories = {}
        self._loaded = False
        for project_id in self.project_ids:
            for track_block in self.track_blocks:
                self.stories.update(dict([(story.id, story) for story in _flatten_list(pt_api.getStories(project_id, track_block, self.token,
                                                                                                   story_constructor=Story.create))]))
        
        self._loaded = True
        print self._loaded
                
    def activity_web_hook(self, activity):
        if activity.event_type == 'story_update':
            for storyxml in activity.stories.iterchildren():
                if storyxml.id in self.stories:
                    self.stories[storyxml.id].update(activity, storyxml)
                    print('Story update %s' % storyxml.id)
        elif activity.event_type == 'story_create':
            for storyxml in activity.stories.iterchildren():
                story = Story.create(activity.project_id, storyxml)
                self.stories[story.id] = story
                print('Create New Story %s' % storyxml.id)
        elif activity.event_type == 'story_delete':
            for storyxml in activity.stories.iterchildren():
                if storyxml.id in self.stories:
                    self.stories[storyxml.id].delete()
                    del self.stories[storyxml.id]
                    print('Story delete %s' % storyxml.id)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Sleuth')
    parser.add_argument('--token', help='The pivotal tracker API token')
    parser.add_argument('--projects', nargs='+', type=int, help='The pivotal tracker project IDs')
    args = parser.parse_args()
    web_app = Sleuth_Web_App(Sleuth(project_ids=args.projects, track_blocks=['current', 'backlog'], token=args.token))
