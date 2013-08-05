from mock import patch, call, MagicMock, Mock
from sleuth import Sleuth, Story
import unittest2


def flatten_list(alist):
    if type(alist) != type([]):
        return [alist]
    return_list = []
    for item in alist:
        return_list.extend(flatten_list(item))
    return return_list


@patch('sleuth.pt_api')
@patch('sleuth.Story')
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
        self.project2_backlog = [[MagicMock(id=14), MagicMock(id=15)], [MagicMock(id=16), MagicMock(id=17), MagicMock(id=18)]]

        self.stories = {}

        self.stories.update(dict([(story.id, story) for story in flatten_list(self.project1_current)]))
        self.stories.update(dict([(story.id, story) for story in flatten_list(self.project1_backlog)]))
        self.stories.update(dict([(story.id, story) for story in flatten_list(self.project2_current)]))
        self.stories.update(dict([(story.id, story) for story in flatten_list(self.project2_backlog)]))

    def wait_for_activity_to_be_processed(self, sleuth):
        max_wait = 5
        waited = 0
        while sleuth.activity_queue and waited < max_wait:
            import time
            time.sleep(1)
            waited += 1

    def test_init(self, Story, pt_api):
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

    def test_activity_web_hook_update(self, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        updatedStory = MagicMock(id=15)
        activity = MagicMock(event_type='story_update')
        activity.stories.iterchildren.return_value = [updatedStory]

        # action
        sleuth.activity_web_hook(activity)

        #confirm
        self.wait_for_activity_to_be_processed(sleuth)
        sleuth.stories[15].update.assert_called_once_with(activity, updatedStory)

    def test_activity_web_hook_move_into_project(self, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        updatedStory = MagicMock(id=15)
        activity = MagicMock(event_type='move_into_project')
        activity.stories.iterchildren.return_value = [updatedStory]

        # action
        sleuth.activity_web_hook(activity)

        #confirm
        self.wait_for_activity_to_be_processed(sleuth)
        sleuth.stories[15].update.assert_called_once_with(activity, updatedStory)

    def test_activity_web_hook_create(self, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        newStory = MagicMock(id=19)
        activity = MagicMock(event_type='story_create')
        activity.stories.iterchildren.return_value = [newStory]
        realNewStory = Story.create.return_value
        # action
        sleuth.activity_web_hook(activity)

        # confirm
        self.wait_for_activity_to_be_processed(sleuth)
        Story.create.assert_called_once_with(activity.project_id, newStory)
        self.assertTrue(sleuth.stories[realNewStory.id] == realNewStory)

    def test_activity_web_hook_delete(self, Story, pt_api):
        # setup
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        sleuth.stories = self.stories
        deletedStory = MagicMock(id=15)
        activity = MagicMock(event_type='story_delete')
        realDeletedStory = sleuth.stories[deletedStory.id]
        activity.stories.iterchildren.return_value = [deletedStory]

        # action
        sleuth.activity_web_hook(activity)

        # confirm
        self.wait_for_activity_to_be_processed(sleuth)
        self.assertTrue(deletedStory.id not in sleuth.stories)
        self.assertTrue(realDeletedStory.delete.called)


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
        del storyxml.notes
        del storyxml.tasks
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
