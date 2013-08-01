import unittest2
from mock import patch, call, MagicMock, Mock
from sleuth import Sleuth, Sleuth_Web_App, Story


def flatten_list(alist):
    if type(alist) != type([]):
        return [alist]
    return_list = []
    for item in alist:
        return_list.extend(flatten_list(item))
    return return_list


@patch('sleuth.pt_api')
@patch('sleuth.Story')
@patch('sleuth.lxml.etree.tostring', MagicMock())
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
        sleuth.stories[15].update.assert_called_with(activity, updatedStory)
         
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
        self.assertTrue(self.stories[realNewStory.id] == realNewStory)
        
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


@patch('sleuth.make_server')
class Test_Sleuth_Web_App(unittest2.TestCase):

    @patch('sleuth.objectify')
    def test__activity_web_hook(self, objectify, make_server):
        #setup
        receiver = MagicMock()
        request = MagicMock()
        webapp = Sleuth_Web_App(receiver, 8080)
        
        # action
        webapp._activity_web_hook(request)
        
        # confirm
        objectify.fromstring.assert_called_once_with(request.body)
        receiver.activity_web_hook.assert_called_once_with(objectify.fromstring.return_value)
