from threading import Lock
import argparse
import datetime
import logging
import operator
import pt_api
import sys
import threading
import time


logger = logging.getLogger(__name__)


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
        self._last_updated = {}

        self.project_ids = project_ids
        new_last_updated = datetime.datetime.now()
        for project_id in self.project_ids:
            self._set_last_updated(new_last_updated, project_id, 'v3')
            self._set_last_updated(new_last_updated, project_id, 'v4')
        self.token = token
        self.track_blocks = track_blocks
        self.stories = {}
        self.update_lock = Lock()
        self.load_stories_thread = threading.Thread(target=self.load_stories())
        self.load_stories_thread.daemon = True
        self.load_stories_thread.start()

    def _set_last_updated(self, new_last_updated, project_id, version):
        if time.daylight:
            last_updated = new_last_updated - datetime.timedelta(hours=1)
        self._last_updated['%s-%s' % (project_id, version)] = last_updated

    def _get_last_updated(self, project_id, version):
        return self._last_updated['%s-%s' % (project_id, version)]

    def load_stories(self):
        ''' Reload the stories from the trackers
        '''
        with self.update_lock:
            for project_id in self.project_ids:
                for track_block in self.track_blocks:
                    self.stories.update(dict([(story.id, story) for story in _flatten_list(pt_api.get_stories(project_id, track_block, self.token,
                                                                                                             story_constructor=Story.create))]))
        logger.info('Stories are loaded')

    def log_unknown_story(self, storyxml):
            logger.warning('Story unknown: %s' % storyxml.id)
            if __debug__:
                logger.debug(pt_api.to_str(storyxml))

    def log_unknown_task(self, taskxml):
            logger.warning('Task unknown: %s' % taskxml.id)
            if __debug__:
                logger.debug(pt_api.to_str(taskxml))

    def log_unknown_comment(self, commentxml):
            logger.warning('Comment unknown: %s' % commentxml.id)
            if __debug__:
                logger.debug(pt_api.to_str(commentxml))

    def getStory(self, storyxml):
        ''' If the story is tracked return it
            else return None and log the unknwon story
        '''
        if storyxml.id in self.stories:
            return self.stories[storyxml.id]
        else:
            self.log_unknown_story(storyxml)

    def getTask(self, story, taskxml):
        if taskxml.id in story.tasks:
            task = story.tasks[taskxml.id]
            return task
        else:
            self.log_unknown_task(taskxml)
            return None

    def process_activity(self, activity):
        ''' To be run in a thread, process all the activities in the queue
        '''
        with self.update_lock:
            logger.info(activity.description)

            if activity.event_type in ['story_update', 'move_into_project']:
                for storyxml in activity.stories.iterchildren():
                    story = self.getStory(storyxml)
                    if story:
                        logger.info('%s: %s' % (activity.event_type, storyxml.id))
                        story.update(activity, storyxml)
                        logger.info("<Updated Story> %s:%s" % (story.id, story.description))

            elif activity.event_type == 'story_create':
                for storyxml in activity.stories.iterchildren():
                    logger.info('%s: %s' % (activity.event_type, storyxml.id))
                    story = Story.create(activity.project_id, storyxml)
                    self.stories[story.id] = story
                    logger.info("<Added Story> %s:%s" % (story.id, story.description))

            elif activity.event_type in ['story_delete', 'multi_story_delete']:
                for storyxml in activity.stories.iterchildren():
                    logger.info('%s: %s' % (activity.event_type, storyxml.id))
                    story = self.getStory(storyxml)
                    if story:
                        del self.stories[storyxml.id]
                        logger.info("<Deleted Story> %s:%s" % (story.id, story.description))
            elif activity.event_type == 'note_create':
                for storyxml in activity.stories.iterchildren():
                    logger.info('%s: %s' % (activity.event_type, storyxml.id))
                    story = self.getStory(storyxml)
                    if story:
                        for notexml in storyxml.notes.iterchildren():
                            note = Note(notexml.id, notexml['text'].text, activity.author, activity.occurred_at)
                            story.notes[note.id] = note
                            logger.info("<Created Note> %s:%s" % (note.id, note.text))

            elif activity.event_type == 'task_create':
                        for storyxml in activity.stories.iterchildren():
                            logger.info('%s: %s' % (activity.event_type, storyxml.id))
                            story = self.getStory(storyxml)
                            if story:
                                for taskxml in storyxml.tasks.iterchildren():
                                    position = getattr(taskxml, 'position', None)
                                    complete = getattr(taskxml, 'complete', False)
                                    created_at = getattr(taskxml, 'created_at', None)
                                    task = Task(taskxml.id, taskxml.description, created_at, position=position, complete=complete)
                                    story.tasks[task.id] = task
                                    logger.info("<Created Task> %s:%s" % (task.id, task.description))

            elif activity.event_type == 'task_edit':
                for storyxml in activity.stories.iterchildren():
                    story = self.getStory(storyxml)
                    if story:
                        logger.info('%s: %s' % (activity.event_type, storyxml.id))
                        for taskxml in storyxml.tasks.iterchildren():
                            task = self.getTask(story, taskxml)
                            if task:
                                task.update(taskxml)
                                logger.info("<Updated Task> %s:%s" % (task.id, task.description))

            elif activity.event_type == 'task_delete':
                for storyxml in activity.stories.iterchildren():
                    story = self.getStory(storyxml)
                    if story:
                        logger.info('%s: %s' % (activity.event_type, storyxml.id))
                        for taskxml in storyxml.tasks.iterchildren():
                            task = self.getTask(story, taskxml)
                            if task:
                                del story.tasks[taskxml.id]
                                logger.info("<Deleted Task> %s:%s" % (task.id, task.description))

            elif activity.event_type == 'comment_delete':
                for storyxml in activity.stories.iterchildren():
                    story = self.getStory(storyxml)
                    if story:
                        logger.info('%s: %s' % (activity.event_type, storyxml.id))
                        for commentxml in storyxml.comments.iterchildren():
                            if commentxml.id in story.notes:
                                note = story.notes[commentxml.id]
                                del story.notes[commentxml.id]
                                logger.info("<Deleted Note> %s:%s" % (note.id, note.text))
                            else:
                                self.log_unknown_comment(commentxml)

            elif activity.event_type in ['move_from_project']:
                # because all the projects are mixed together move_from_project event_type can be ignored
                pass

            else:
                logger.warning('Unknown event type: %s' % activity.event_type)
                if __debug__:
                    logger.debug(pt_api.to_str(activity))

    def collect_task_updates(self):
        """ Update the stories since the last time this method was called.
        """
        def getLastUpdated(project_id, version):
            new_last_updated = datetime.datetime.now() - datetime.timedelta(seconds=1)
            last_updated = self._get_last_updated(project_id, version)
            self._set_last_updated(new_last_updated, project_id, version)
            if __debug__:
                logger.debug('%s-%s: %s' % (project_id, version, last_updated))
            return last_updated

        for project_id in self.project_ids:
            last_updated = getLastUpdated(project_id, 'v3')
            activitiesxml = pt_api.get_project_activities_v3(project_id, last_updated, self.token)
            if activitiesxml is not None:
                activities = [activityxml for activityxml in activitiesxml.iterchildren()]
                activities.sort(key=operator.attrgetter('occurred_at'))
                for activityxml in activities:
                    logger.info('--------------------')
                    logger.info('')
                    logger.info('--------------------')
                    logger.info(activityxml.event_type)
                    self.process_activity(activityxml)

            last_updated = getLastUpdated(project_id, 'v4')
            activitiesxml = pt_api.get_project_activities(project_id, last_updated, self.token)
            if activitiesxml is not None:
                activities = [activityxml for activityxml in activitiesxml.iterchildren()]
                activities.sort(key=operator.attrgetter('occurred_at'))
                for activityxml in activities:
                    if activityxml.event_type in ['task_delete', 'task_edit', 'task_create', 'comment_delete']:
                        logger.info('--------------------')
                        logger.info('')
                        logger.info('--------------------')
                        logger.info(activityxml.event_type)
                        self.process_activity(activityxml)


def continue_tracking():
    return True


def main(input_args=None):

    def parse_logging_level(log_level):
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % log_level)
        return numeric_level


    if input_args is None:
        input_args = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Sleuth')
    parser.add_argument('--token', help='The pivotal tracker API token')
    parser.add_argument('--projects', nargs='+', type=int, help='The pivotal tracker project IDs')
    parser.add_argument('--log-file', dest='log_file', type=str, default=None, help='Where to log the output to.')
    parser.add_argument('--log-file-level', dest='log_file_level', type=str, default='WARNING', help='The file logger level.')
    parser.add_argument('--log-level', dest='log_level', type=str, default='INFO', help='The stream logger level.')
    args = parser.parse_args(input_args)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s/+%(relativeCreated)7.0f|%(levelname)s| %(filename)s:%(lineno)-4s | %(message)s")
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(parse_logging_level(args.log_level))
    logger.addHandler(stream_handler)

    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        formatter = logging.Formatter("%(asctime)s/+%(relativeCreated)7.0f|%(levelname)s| %(filename)s:%(lineno)-4s | %(message)s")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(parse_logging_level(args.log_file_level))
        logger.addHandler(file_handler)

    sleuth = Sleuth(project_ids=args.projects, track_blocks=['current', 'backlog', 'icebox'], token=args.token)
    while continue_tracking():
        sleuth.collect_task_updates()
        time.sleep(1)
