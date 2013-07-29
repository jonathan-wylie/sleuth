import unittest2
from mock import patch
from sleuth import Sleuth


class Test_Sleuth(unittest2.TestCase):
    
    def setUp(self):
        self.project_ids = [1, 2]
        self.track_blocks = ['current', 'backlog']
        self.token = '--token--'

    @patch('sleuth.Sleuth.pt_api')
    def Test_init(self, pt_api):
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)
        self.assertEqual(sleuth.project_ids, self.project_ids)
        self.assertEqual(sleuth.token, self.token)
        self.assertEqual(sleuth.track_blocks, self.track_blocks)
        #self.stories[project_id][track_block] = pt_api.getStories(project_id, track_block, self.token,
        #                                                          story_constructor=Story.create_from_load)
        #print self.stories[project_id][track_block]
        print pt_api.getStories.call_args_list

    def Test_activity_web_hook_update(self, pt_api):
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)

    def Test_activity_web_hook_create(self, pt_api):
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)

    def Test_activity_web_hook_delete(self, pt_api):
        sleuth = Sleuth(self.project_ids, self.track_blocks, self.token)


class Test_Story(unittest2.TestCase):

    def Test_create(self):
        pass

    def Test_create_from_load(self):
        pass

    def Test_init(self):
        pass
    
    def Test_update(self):
        pass

    def Test_delete(self):
        pass


class Test_Sleuth_Web_App(unittest2.TestCase):

    def __init__(self):
        pass
    
    def __activity_web_hook(self):
        pass