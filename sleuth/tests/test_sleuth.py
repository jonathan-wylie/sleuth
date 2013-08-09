from mock import patch, call, MagicMock, Mock
import unittest2
from sleuth import Sleuth, Story, Task


def flatten_list(alist):
    if type(alist) != type([]):
        return [alist]
    return_list = []
    for item in alist:
        return_list.extend(flatten_list(item))
    return return_list


@patch('sleuth.pt_api')
@patch('sleuth.Story')
@patch('sleuth.Sleuth.log_unknown_story')
@patch('sleuth.pt_api.to_str', MagicMock())
@patch('sleuth.Sleuth.collect_task_updates', MagicMock())
class Test_Sleuth(unittest2.TestCase):

    def setUp(self):
        self.project_ids = [1, 2]
        self.track_blocks = ['current', 'backlog']
        self.token = '--token--'
        self.project1_current = [MagicMock(id=1), MagicMock(id=2), MagicMock(id=3), MagicMock(id=4), MagicMock(id=5)]
        self.project1_backlog = [[MagicMock(id=6), MagicMock(id=7), MagicMock(id=8)], [MagicMock(id=9), MagicMock(id=10)]]
        self.project2_current = [MagicMock(id=11), MagicMock(id=12), MagicMock(id=13)]
        self.project2_backlog = [[MagicMock(id=14), MagicMock(id=15, notes={1: MagicMock(id=1)}, tasks={1: MagicMock(id=1)})], [MagicMock(id=16), MagicMock(id=17), MagicMock(id=18)]]

        self.stories = {}

        self.stories.update(dict([(story.id, story) for story in flatten_list(self.project1_current)]))
        self.stories.update(dict([(story.id, story) for story in flatten_list(self.project1_backlog)]))
        self.stories.update(dict([(story.id, story) for story in flatten_list(self.project2_current)]))
        self.stories.update(dict([(story.id, story) for story in flatten_list(self.project2_backlog)]))

    def test_init(self, log_unknown_story, Story, pt_api):
        # setup
        pt_api.get_stories.side_effect = [self.project1_current, self.project1_backlog, self.project2_current, self.project2_backlog]

        # action
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)

        # confirm
        self.assertEqual(sleuth.project_ids, self.project_ids)
        self.assertEqual(sleuth.token, self.token)
        self.assertEqual(sleuth.track_blocks, self.track_blocks)

        expected_get_story_calls = [call(1, 'current', self.token, story_constructor=Story.create),
                                    call(1, 'backlog', self.token, story_constructor=Story.create),
                                    call(2, 'current', self.token, story_constructor=Story.create),
                                    call(2, 'backlog', self.token, story_constructor=Story.create)]
        self.assertListEqual(expected_get_story_calls, pt_api.get_stories.call_args_list)

        self.assertDictEqual(self.stories, sleuth.stories)

    def test_process_activity_story_update(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        updated_story = MagicMock(id=15)
        activity = MagicMock(event_type='story_update')
        activity.stories.iterchildren.return_value = [updated_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        sleuth.stories[15].update.assert_called_once_with(activity, updated_story)

    def test_process_activity_story_update_unknown_story(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = {}
        updated_story = MagicMock(id=15)
        activity = MagicMock(event_type='story_update')
        activity.stories.iterchildren.return_value = [updated_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        log_unknown_story.assert_called_once_with(updated_story)

    def test_process_activity_story_move_into_project(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        moved_story = MagicMock(id=15)
        activity = MagicMock(event_type='move_into_project')
        activity.stories.iterchildren.return_value = [moved_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        sleuth.stories[15].update.assert_called_once_with(activity, moved_story)

    def test_process_activity_story_create(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        created_story = MagicMock(id=19)
        activity = MagicMock(event_type='story_create')
        activity.stories.iterchildren.return_value = [created_story]
        realNewStory = Story.create.return_value
        # action
        sleuth.process_activity(activity)

        # confirm
        Story.create.assert_called_once_with(activity.project_id, created_story)
        self.assertTrue(sleuth.stories[realNewStory.id] == realNewStory)

    def test_process_activity_story_delete(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        deleted_story = MagicMock(id=15)
        activity = MagicMock(event_type='story_delete')
        activity.stories.iterchildren.return_value = [deleted_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        self.assertTrue(deleted_story.id not in sleuth.stories)

    def test_process_activity_delete_unknown_story(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = {}
        deleted_story = MagicMock(id=15)
        activity = MagicMock(event_type='story_delete')
        activity.stories.iterchildren.return_value = [deleted_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        log_unknown_story.assert_called_once_with(deleted_story)

    def test_process_activity_note_create_unknown_story(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = {}
        note_create_story = MagicMock(id=15)
        activity = MagicMock(event_type='note_create')
        activity.stories.iterchildren.return_value = [note_create_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        log_unknown_story.assert_called_once_with(note_create_story)

    def test_process_activity_note_create(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        note_create_story = MagicMock(id=15)
        notexml = MagicMock()
        note_create_story.notes.iterchildren.return_value = [notexml]
        activity = MagicMock(event_type='note_create')
        activity.stories.iterchildren.return_value = [note_create_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        self.assertEqual(sleuth.stories[note_create_story.id].notes[notexml.id].id, notexml.id)

    def test_process_activity_task_create(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        task_create_story = MagicMock(id=15)
        taskxml = MagicMock()
        task_create_story.tasks.iterchildren.return_value = [taskxml]
        activity = MagicMock(event_type='task_create')
        activity.stories.iterchildren.return_value = [task_create_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        self.assertEqual(sleuth.stories[task_create_story.id].tasks[taskxml.id].id, taskxml.id)

    def test_process_activity_task_delete(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        task_deletes_story = MagicMock(id=15)
        taskxml = MagicMock(id=1)
        task_deletes_story.tasks.iterchildren.return_value = [taskxml]
        activity = MagicMock(event_type='task_delete')
        activity.stories.iterchildren.return_value = [task_deletes_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        self.assertNotIn(taskxml.id, sleuth.stories[task_deletes_story.id].tasks)

    def test_process_activity_task_update(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        task_updated_story = MagicMock(id=15)
        taskxml = MagicMock(id=1, complete=True)
        task_updated_story.tasks.iterchildren.return_value = [taskxml]
        activity = MagicMock(event_type='task_edit')
        activity.stories.iterchildren.return_value = [task_updated_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        sleuth.stories[task_updated_story.id].tasks[taskxml.id].update.assert_called_once_with(taskxml)

    def test_process_activity_comment_delete(self, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        comment_delete_story = MagicMock(id=15)
        commentxml = MagicMock(id=1)
        comment_delete_story.comments.iterchildren.return_value = [commentxml]
        activity = MagicMock(event_type='comment_delete')
        activity.stories.iterchildren.return_value = [comment_delete_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        self.assertNotIn(commentxml.id, sleuth.stories[comment_delete_story.id].notes)
    
    @patch('sleuth.logger')
    def test_process_activity_unknown_event(self, logger, log_unknown_story, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        comment_delete_story = MagicMock(id=15)
        commentxml = MagicMock(id=1)
        comment_delete_story.comments.iterchildren.return_value = [commentxml]
        activity = MagicMock(event_type='sdhghsldjh176581347687sghfvsdjlh87e5923878')
        activity.stories.iterchildren.return_value = [comment_delete_story]

        # action
        sleuth.process_activity(activity)

        # confirm
        logger.warning.assert_called_once_with('Unknown event type: sdhghsldjh176581347687sghfvsdjlh87e5923878')


class Test_Story(unittest2.TestCase):

    def test_get_data_from_story_xml(self):
        # setup
        storyxml = Mock(story_type='story_type', current_state='current_state', description='description',
                        requested_by='requested_by', created_at='created_at', labels='labels')

        del storyxml.url
        del storyxml.estimate
        del storyxml.name
        del storyxml.owned_by
        del storyxml.accepted_at

        notexml1 = MagicMock()
        notexml2 = MagicMock()
        storyxml.notes.iterchildren.return_value = [notexml1, notexml2]

        taskxml1 = MagicMock()
        taskxml2 = MagicMock()
        storyxml.tasks.iterchildren.return_value = [taskxml1, taskxml2]

        # note = Note(notexml.id, notexml['text'].text, notexml.author, notexml.noted_at)
        #         notes[note.id] = note

        # action
        data = Story.get_data_from_story_xml(storyxml)

        # confirm
        self.assertEqual(data['story_type'], storyxml.story_type)
        self.assertEqual(data['current_state'], storyxml.current_state)
        self.assertEqual(data['description'], storyxml.description)
        self.assertEqual(data['requested_by'], storyxml.requested_by)
        self.assertEqual(data['created_at'], storyxml.created_at)
        self.assertEqual(data['labels'], storyxml.labels)

        self.assertEqual(data['url'], None)
        self.assertEqual(data['estimate'], None)
        self.assertEqual(data['name'], None)
        self.assertEqual(data['owned_by'], None)
        self.assertEqual(data['accepted_at'], None)

        self.assertEqual(data['notes'][notexml1.id].id, notexml1.id)
        self.assertEqual(data['notes'][notexml2.id].id, notexml2.id)

        self.assertEqual(data['tasks'][taskxml1.id].id, taskxml1.id)
        self.assertEqual(data['tasks'][taskxml2.id].id, taskxml2.id)

    def test_create_with_labels(self):
        # setup
        storyxml = MagicMock(story_type='story_type', current_state='current_state', description='description',
                        requested_by='requested_by', created_at='created_at', labels='labels')
        del storyxml.url
        del storyxml.estimate
        del storyxml.name
        del storyxml.owned_by
        del storyxml.accepted_at
        del storyxml.notes
        del storyxml.tasks

        project_id = 1

        # action
        story = Story.create(project_id, storyxml)

        # confirm
        self.assertEqual(story.story_type, storyxml.story_type)
        self.assertEqual(story.current_state, storyxml.current_state)
        self.assertEqual(story.description, storyxml.description)
        self.assertEqual(story.requested_by, storyxml.requested_by)
        self.assertEqual(story.created_at, storyxml.created_at)
        self.assertEqual(story.labels, storyxml.labels.split(','))

        self.assertEqual(story.url, None)
        self.assertEqual(story.estimate, None)
        self.assertEqual(story.name, None)
        self.assertEqual(story.owned_by, None)
        self.assertEqual(story.accepted_at, None)

    def test_create_without_labels(self):
        # setup
        storyxml = MagicMock(story_type='story_type', current_state='current_state', description='description',
                        requested_by='requested_by', created_at='created_at')
        del storyxml.url
        del storyxml.estimate
        del storyxml.name
        del storyxml.owned_by
        del storyxml.accepted_at
        del storyxml.labels
        del storyxml.notes
        del storyxml.tasks

        project_id = 1

        # action
        story = Story.create(project_id, storyxml)

        # confirm
        self.assertEqual(story.story_type, storyxml.story_type)
        self.assertEqual(story.current_state, storyxml.current_state)
        self.assertEqual(story.description, storyxml.description)
        self.assertEqual(story.requested_by, storyxml.requested_by)
        self.assertEqual(story.created_at, storyxml.created_at)
        self.assertEqual(story.labels, [])

        self.assertEqual(story.url, None)
        self.assertEqual(story.estimate, None)
        self.assertEqual(story.name, None)
        self.assertEqual(story.owned_by, None)
        self.assertEqual(story.accepted_at, None)

    def test_update_story_details(self):
        # setup
        storyxml = Mock(story_type='story_type', current_state='current_state', description='description',
                        requested_by='requested_by', created_at='created_at')
        del storyxml.url
        del storyxml.estimate
        del storyxml.name
        del storyxml.owned_by
        del storyxml.accepted_at
        del storyxml.labels
        del storyxml.notes
        del storyxml.tasks

        project_id = 1
        story = Story.create(project_id, storyxml)
        activity = MagicMock(project_id=project_id)

        update_storyxml = MagicMock(story_type='different_story_type', description='new description')
        del update_storyxml.url
        del update_storyxml.estimate
        del update_storyxml.name
        del update_storyxml.owned_by
        del update_storyxml.accepted_at
        del update_storyxml.labels
        del update_storyxml.current_state
        del update_storyxml.requested_by
        del update_storyxml.created_at

        # action
        story.update(activity, update_storyxml)

        # confirm
        self.assertEqual(story.story_type, update_storyxml.story_type)
        self.assertEqual(story.current_state, storyxml.current_state)
        self.assertEqual(story.description, update_storyxml.description)
        self.assertEqual(story.requested_by, storyxml.requested_by)
        self.assertEqual(story.created_at, storyxml.created_at)
        self.assertEqual(story.labels, [])

        self.assertEqual(story.url, None)
        self.assertEqual(story.estimate, None)
        self.assertEqual(story.name, None)
        self.assertEqual(story.owned_by, None)
        self.assertEqual(story.accepted_at, None)

    def test_update_story_project(self):
        # setup
        storyxml = MagicMock(story_type='story_type', current_state='current_state', description='description',
                        requested_by='requested_by', created_at='created_at')
        del storyxml.url
        del storyxml.estimate
        del storyxml.name
        del storyxml.owned_by
        del storyxml.accepted_at
        del storyxml.labels
        project_id = 1
        new_project_id = 2
        story = Story.create(project_id, storyxml)
        activity = MagicMock(project_id=new_project_id)

        update_storyxml = MagicMock()
        del update_storyxml.url
        del update_storyxml.estimate
        del update_storyxml.name
        del update_storyxml.owned_by
        del update_storyxml.accepted_at
        del update_storyxml.labels
        del update_storyxml.current_state
        del update_storyxml.requested_by
        del update_storyxml.created_at
        del update_storyxml.story_type
        del update_storyxml.description

        # action
        story.update(activity, update_storyxml)

        # confirm
        self.assertEqual(story.project_id, new_project_id)


class Test_Task(unittest2.TestCase):

    def test_init(self):
        # setup
        task_id = 1
        description = 'description'
        position = 3
        complete = False
        created_at = 'created_at'

        # action
        task = Task(task_id, description, created_at, position=position, complete=complete)

        # confirm
        self.assertEqual(task_id, task.id)
        self.assertEqual(description, task.description)
        self.assertEqual(position, task.position)
        self.assertEqual(complete, task.complete)

    def test_update_description(self):
        # setup
        task_id = 1
        description = 'description'
        position = 3
        complete = False
        created_at = 'created_at'
        task = Task(task_id, description, created_at, position=position, complete=complete)
        taskxml = MagicMock(description='new description')
        del taskxml.complete
        del taskxml.position

        # action
        task.update(taskxml)

        #confirm
        self.assertEqual(taskxml.description, task.description)

    def test_update_complete(self):
        # setup
        task_id = 1
        description = 'description'
        position = 3
        complete = False
        created_at = 'created_at'
        task = Task(task_id, description, created_at, position=position, complete=complete)
        taskxml = MagicMock(complete=True)
        del taskxml.description
        del taskxml.position

        # action
        task.update(taskxml)

        # confirm
        self.assertEqual(taskxml.complete, task.complete)

    def test_update_position(self):
        # setup
        task_id = 1
        description = 'description'
        position = 3
        complete = False
        created_at = 'created_at'
        task = Task(task_id, description, created_at, position=position, complete=complete)
        taskxml = MagicMock(position=2)
        del taskxml.complete
        del taskxml.description

        # action
        task.update(taskxml)

        #confirm
        self.assertEqual(taskxml.position, task.position)
