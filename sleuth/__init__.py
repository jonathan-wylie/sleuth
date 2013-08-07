from threading import Lock
import datetime
import pt_api
import threading
import time
import logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s/+%(relativeCreated)7.0f|%(levelname)s| %(filename)s:%(lineno)-4s | %(message)s")
logger = logging.getLogger('sleuth')


class Note(object):
    """Represent a note for a story"""

    def __init__(self, note_id, text, author, noted_at):
        self.id = note_id
        self.text = text
        self.author = author
        self.noted_at = noted_at


class Task(object):
    """ Represent a task for a story
    """

    def __init__(self, task_id, description, created_at, position=None, complete=False):
        self.id = task_id
        self.description = description
        self.position = position
        self.complete = complete
        self.created_at = created_at

    def update(self, taskxml):
        if hasattr(taskxml, 'description'):
            logger.info("Changed task description from %s to %s" % (self.description, taskxml.description))
            self.description = taskxml.description
        if hasattr(taskxml, 'complete'):
            logger.info("Changed task completion from %s to %s" % (self.complete, taskxml.complete))
            self.complete = taskxml.complete
        if hasattr(taskxml, 'position'):
            logger.info("Changed task position from %s to %s" % (self.position, taskxml.position))
            self.position = taskxml.position


class Story(object):
    '''The class represents a Pivotal Tracker User Story'''

    @staticmethod
    def get_data_from_story_xml(storyxml):
        data = {}
        for attribute in ['story_type', 'url', 'estimate', 'current_state', 'description',
                          'name', 'requested_by', 'owned_by', 'created_at', 'accepted_at', 'labels']:
            data[attribute] = getattr(storyxml, attribute, None)
        notes = {}
        if hasattr(storyxml, 'notes'):
            for notexml in storyxml.notes.iterchildren():
                note = Note(notexml.id, notexml['text'].text, notexml.author, notexml.noted_at)
                notes[note.id] = note
        else:
            notes = None
        data['notes'] = notes
        tasks = {}
        if hasattr(storyxml, 'tasks'):
            for taskxml in storyxml.tasks.iterchildren():
                task = Task(taskxml.id, taskxml.description, taskxml.created_at, position=taskxml.position, complete=taskxml.complete)
                tasks[task.id] = task
        else:
            tasks = None
        data['tasks'] = tasks
        return data

    @staticmethod
    def create(project_id, storyxml):
        data = Story.get_data_from_story_xml(storyxml)
        return Story(storyxml.id, project_id,
                    data['story_type'], data['url'], data['estimate'], data['current_state'],
                    data['description'], data['name'], data['requested_by'], data['owned_by'],
                    data['notes'], data['tasks'], data['created_at'], data['accepted_at'], data['labels'])

    def __init__(self, story_id, project_id, story_type, url, estimate, current_state, description, name, requested_by,
                 owned_by, notes, tasks, created_at, accepted_at, labels):
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
            self.labels = str(labels).split(',')
        if notes == None:
            self.notes = {}
        else:
            self.notes = notes
        if tasks == None:
            self.tasks = {}
        else:
            self.tasks = tasks

    def update(self, activity, storyxml):

        # Update story attributes
        data = Story.get_data_from_story_xml(storyxml)
        for attribute, new_value in data.items():
            oldValue = getattr(self, attribute)
            if new_value is not None and new_value != oldValue:
                logger.info("Changed story %s from %s to %s" % (attribute, oldValue, new_value))
                setattr(self, attribute, new_value)

        # Update the project_id if needed
        project_id = activity.project_id
        if self.project_id != project_id:
            logger.info('Changed story project_id changed from %s to %s' % (self.project_id, project_id))
            self.project_id = project_id

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
        self.load_stories_thread = threading.Thread(target=self.load_stories())
        self.load_stories_thread.daemon = True
        self.load_stories_thread.start()
        self.activity_queue = []
        self.process_activities_thread = threading.Thread(target=self._process_activities)
        self.process_activities_thread.daemon = True
        self.process_activities_thread.start()
        self.collect_task_updates()

    def load_stories(self):
        ''' Reload the stories from the trackers
        '''
        with self.update_lock:
            for project_id in self.project_ids:
                for track_block in self.track_blocks:
                    self.stories.update(dict([(story.id, story) for story in _flatten_list(pt_api.get_stories(project_id, track_block, self.token,
                                                                                                             story_constructor=Story.create))]))
        logger.info('Stories are loaded')

    def activity_web_hook(self, activity):
        ''' Add the story changes to a queue to be processed
        '''
        self.activity_queue.append(activity)

    def log_unkown_story(self, storyxml):
            logger.warning('Story unknown: %s' % storyxml.id)
            if __debug__:
                logger.debug(pt_api.to_str(storyxml))

    def _process_activities(self):
        ''' To be run in a thread, process all the activities in the queue
        '''

        while True:
            if self.activity_queue:
                activity = self.activity_queue[0]
                with self.update_lock:
                    logger.info('--------------------')
                    logger.info('')
                    logger.info('--------------------')
                    logger.info(activity.description)

                    if activity.event_type in ['story_update', 'move_into_project']:
                        for storyxml in activity.stories.iterchildren():
                            if storyxml.id in self.stories:
                                story = self.stories[storyxml.id]
                                logger.info('%s: %s' % (activity.event_type, storyxml.id))
                                story.update(activity, storyxml)
                                logger.info("<Updated Story> %s:%s" % (story.id, story.description))
                            else:
                                self.log_unkown_story(storyxml)

                    elif activity.event_type == 'story_create':
                        for storyxml in activity.stories.iterchildren():
                            logger.info('%s: %s' % (activity.event_type, storyxml.id))
                            story = Story.create(activity.project_id, storyxml)
                            self.stories[story.id] = story
                            logger.info("<Added Story> %s:%s" % (story.id, story.description))

                    elif activity.event_type == 'story_delete':
                        for storyxml in activity.stories.iterchildren():
                            logger.info('%s: %s' % (activity.event_type, storyxml.id))
                            if storyxml.id in self.stories:
                                story = self.stories[storyxml.id]
                                self.stories[storyxml.id].delete()
                                del self.stories[storyxml.id]
                                logger.info("<Deleted Story> %s:%s" % (story.id, story.description))
                            else:
                                self.log_unkown_story(storyxml)

                    elif activity.event_type == 'note_create':
                        for storyxml in activity.stories.iterchildren():
                            logger.info('%s: %s' % (activity.event_type, storyxml.id))
                            if storyxml.id in self.stories:
                                story = self.stories[storyxml.id]
                                for notexml in storyxml.notes.iterchildren():
                                    note = Note(notexml.id, notexml['text'].text, activity.author, activity.occurred_at)
                                    story.notes[note.id] = note
                                    logger.info("<Created Note> %s:%s" % (note.id, note.text))
                            else:
                                self.log_unkown_story(storyxml)

                    elif activity.event_type == 'task_create':
                        for storyxml in activity.stories.iterchildren():
                            logger.info('%s: %s' % (activity.event_type, storyxml.id))
                            if storyxml.id in self.stories:
                                for taskxml in storyxml.tasks.iterchildren():
                                    story = self.stories[storyxml.id]
                                    position = getattr(taskxml, 'position', None)
                                    complete = getattr(taskxml, 'complete', False)
                                    created_at = getattr(taskxml, 'created_at', None)
                                    task = Task(taskxml.id, taskxml.description, created_at, position=position, complete=complete)
                                    story.tasks[task.id] = task
                                    logger.info("<Created Task> %s:%s" % (task.id, task.description))
                            else:
                                self.log_unkown_story(storyxml)

                    elif activity.event_type == 'task_edit':
                        for storyxml in activity.stories.iterchildren():
                            if storyxml.id in self.stories:
                                logger.info('%s: %s' % (activity.event_type, storyxml.id))
                                story = self.stories[storyxml.id]
                                for taskxml in storyxml.tasks.iterchildren():
                                    if taskxml.id in story.tasks:
                                        task = story.tasks[taskxml.id]
                                        task.update(taskxml)
                                        logger.info("<Updated Task> %s:%s" % (task.id, task.description))
                                    else:
                                        logger.info('Task unknown: %s' % taskxml.id)
                            else:
                                self.log_unkown_story(storyxml)

                    elif activity.event_type == 'task_delete':
                        for storyxml in activity.stories.iterchildren():
                            if storyxml.id in self.stories:
                                logger.info('%s: %s' % (activity.event_type, storyxml.id))
                                story = self.stories[storyxml.id]
                                for taskxml in storyxml.tasks.iterchildren():
                                    if taskxml.id in story.tasks:
                                        task = story.tasks[taskxml.id]
                                        del story.tasks[taskxml.id]
                                        logger.info("<Deleted Task> %s:%s" % (task.id, task.description))
                                    else:
                                        logger.info('Task unknown: %s' % taskxml.id)
                            else:
                                self.log_unkown_story(storyxml)

                    elif activity.event_type == 'comment_delete':
                        for storyxml in activity.stories.iterchildren():
                            if storyxml.id in self.stories:
                                logger.info('%s: %s' % (activity.event_type, storyxml.id))
                                story = self.stories[storyxml.id]
                                for commentxml in storyxml.comments.iterchildren():
                                    if commentxml.id in story.notes:
                                        note = story.notes[commentxml.id]
                                        del story.notes[commentxml.id]
                                        logger.info("<Deleted Note> %s:%s" % (note.id, note.text))
                                    else:
                                        logger.info('Comment Unknown: %s' % commentxml.id)
                            else:
                                self.log_unkown_story(storyxml)

                    elif activity.event_type in ['move_from_project']:
                        # because all the projects are mixed together move_from_project event_type can be ignored
                        pass

                    else:
                        logger.warning('Unknown event type: %s' % activity.event_type)
                        if __debug__:
                            logger.debug(pt_api.to_str(activity))
                    # Only take it off the queue when it has finished
                    # only for the purposes of the unit tests, so they can tell when the
                    # activity has been processed.
                    activity = self.activity_queue.pop(0)
            else:
                time.sleep(1)


    def collect_task_updates(self):

        def get_activities():
            lastCheck = datetime.datetime.now()
            if time.daylight:
                    lastCheck = lastCheck - datetime.timedelta(hours=1)
            while True:
                check = datetime.datetime.now()
                if time.daylight:
                    check = check - datetime.timedelta(hours=1)
                for project_id in self.project_ids:
                    activitiesxml = pt_api.get_project_activities_v3(project_id, lastCheck, self.token)
                    for activityxml in activitiesxml.iterchildren():
                        logger.info(activityxml.event_type)
                        self.activity_queue.append(activityxml)
                    activitiesxml = pt_api.get_project_activities(project_id, lastCheck, self.token)
                    for activityxml in activitiesxml.iterchildren():
                        if activityxml.event_type in ['task_delete', 'task_edit', 'task_create', 'comment_delete']:
                            logger.info(activityxml.event_type)
                            self.activity_queue.append(activityxml)
                lastCheck = check
                time.sleep(1)

        self.collect_task_thread = threading.Thread(target=get_activities)
        self.collect_task_thread.start()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Sleuth')
    parser.add_argument('--token', help='The pivotal tracker API token')
    parser.add_argument('--projects', nargs='+', type=int, help='The pivotal tracker project IDs')
    parser.add_argument('--port', type=int, help='The port the activity_web_hook should listening on')
    args = parser.parse_args()
    sleuth = Sleuth(project_ids=args.projects, track_blocks=['current', 'backlog'], token=args.token)
    while True:
        time.sleep(60)
