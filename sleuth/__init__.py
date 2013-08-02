from lxml import objectify
from pyramid.config import Configurator
from pyramid.response import Response
from wsgiref.simple_server import make_server
import lxml
import pt_api
from threading import Lock, Thread
import time


class Sleuth_Web_App(object):
    '''This class listens for pivotal tracker activity posts, and publishes them.'''
    
    def __init__(self, activity_receiver, port):
        self.__activity_receiver = activity_receiver
        self.__port = port
        self.__config = Configurator()
        self.__config.add_route('activity_web_hook', '/activity_web_hook')
        self.__config.add_view(self._activity_web_hook, route_name='activity_web_hook', request_method='POST')
        self.__app = self.__config.make_wsgi_app()
        self.__server = make_server('0.0.0.0', self.__port, self.__app)
        self.__server.serve_forever()
    
    def _activity_web_hook(self, request):
        activity = objectify.fromstring(request.body)
        self.__activity_receiver.activity_web_hook(activity)
        return Response('OK')


class Story(object):
    '''The class represents a Pivotal Tracker User Story'''

    @staticmethod
    def get_data_from_story_xml(storyxml):
        data = {}

        for attribute in ["story_type", "url", "estimate", "current_state", "description",
                          "name", "requested_by", "owned_by", "created_at", "accepted_at", "labels"]:
            if hasattr(storyxml, attribute):
                data[attribute] = getattr(storyxml, attribute)
            else:
                data[attribute] = None

        return data

    @staticmethod
    def create(project_id, storyxml):
        data = Story.get_data_from_story_xml(storyxml)
        return Story(storyxml.id, project_id,
                    data['story_type'], data['url'], data['estimate'], data['current_state'],
                    data['description'], data['name'], data['requested_by'], data['owned_by'],
                    data['created_at'], data['accepted_at'], data['labels'])
       
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
        if labels == None:
            self.labels = []
        else:
            self.labels = labels.split(',')
    
    def update(self, activity, storyxml):
        
        data = Story.get_data_from_story_xml(storyxml)
        for attribute, new_value in data.items():
                oldValue = getattr(self, attribute)
                if new_value is not None and new_value != oldValue:
                    print "%s changed from %s to %s" % (attribute, oldValue, new_value)
                    setattr(self, attribute, new_value)
        
        try:
            project_id = activity.project_id
            if self.project_id != project_id:
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
        self.update_lock = Lock()
        self.load_stories_thread = Thread(target=self.load_stories())
        self.load_stories_thread.daemon = True
        self.load_stories_thread.start()
        self.activity_queue = []
        self.process_activities_thread = Thread(target=self._process_activities)
        self.process_activities_thread.daemon = True
        self.process_activities_thread.start()
    
    def load_stories(self):
        """ Reload the stories from the trackers
        """
        with self.update_lock:
            for project_id in self.project_ids:
                for track_block in self.track_blocks:
                    self.stories.update(dict([(story.id, story) for story in _flatten_list(pt_api.get_stories(project_id, track_block, self.token,
                                                                                                             story_constructor=Story.create))]))
        print "Stories are loaded"
    
    def activity_web_hook(self, activity):
        """ Add the story changes to a queue to be processed
        """
        self.activity_queue.append(activity)
        
    def _process_activities(self):
        """ To be run in a thread, process all the activities in the queue
        """
        while True:
            if self.activity_queue:
                activity = self.activity_queue.pop()
                with self.update_lock:
                    if activity.event_type == 'story_update':
                        for storyxml in activity.stories.iterchildren():
                            if storyxml.id in self.stories:
                                self.stories[storyxml.id].update(activity, storyxml)
                                print('Story update %s' % storyxml.id)
                            else:
                                print('Story unknown: %s' % storyxml.id)
                                print lxml.etree.tostring(storyxml)
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
                            else:
                                print('Story unknown: %s' % storyxml.id)
                                print lxml.etree.tostring(storyxml)
                    elif activity.event_type == 'move_into_project':
                        for storyxml in activity.stories.iterchildren():
                            if storyxml.id in self.stories:
                                self.stories[storyxml.id].update(activity, storyxml)
                                print('Story move into project %s' % storyxml.id)
                            else:
                                print('Story unknown: %s' % storyxml.id)
                                print lxml.etree.tostring(storyxml)
                    elif activity.event_type == 'move_from_project':
                        pass
                        # because all the projects are mixed together move_from_project event_type can be ignored
                    else:
                        print('Unknown event type: %s' % activity.event_type)
                        print lxml.etree.tostring(activity)
            else:
                time.sleep(1)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Sleuth')
    parser.add_argument('--token', help='The pivotal tracker API token')
    parser.add_argument('--projects', nargs='+', type=int, help='The pivotal tracker project IDs')
    parser.add_argument('--port', type=int, help='The port the activity_web_hook should listening on')
    args = parser.parse_args()
    web_app = Sleuth_Web_App(Sleuth(project_ids=args.projects, track_blocks=['current', 'backlog', 'icebox'], token=args.token), port=args.port)
