import unittest2
from mock import patch
from sleuth import pt_api


class Test_APICall(unittest2.TestCase):
    
    @patch('sleuth.pt_api.subprocess')
    def Test_APICall(self, subprocess):
        # setup
        url = 'http://www.myurl.co.uk/blah?stuff=things'
        token = 'xxxxxxxxxx'
        stdout_data = 'std_out'
        subprocess.Popen.return_value.communicate.return_value = (stdout_data, 'std_in')
        
        # action
        data = pt_api.APICall(url, token)
        
        # confirm
        subprocess.Popen.assert_called_once_with("curl -H 'X-TrackerToken: xxxxxxxxxx' -X GET http://www.myurl.co.uk/blah?stuff=things",
                                                 shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        self.assertEqual(stdout_data, data)


@patch('sleuth.pt_api.APICall')
class Test_getStories(unittest2.TestCase):
    
    def setUp(self):
        self.token = 'xxxxxxxxxx'
        self.project_id = 1
        self.iterations_reponse = """<?xml version="1.0" encoding="UTF-8"?>
    <iterations type="array">
      <iteration>
        <id type="integer">1</id>
        <number type="integer">1</number>
        <start type="datetime">2009/03/16 00:00:00 UTC</start>
        <finish type="datetime">2009/03/23 00:00:00 UTC</finish>
        <team_strength type="float">0.75</team_strength>
        <stories type="array">
          <story>
            <id type="integer">0</id>
            <project_id type=\"integer\">1</project_id>
            <story_type>feature</story_type>
            <url>$STORY_URL</url>
            <estimate type="integer">2</estimate>
            <current_state>accepted</current_state>
            <description>Windoze Save Dialog thingy</description>
            <name>The Save Dialog 1</name>
            <requested_by>Dana Deer</requested_by>
            <owned_by>Rob</owned_by>
            <created_at type="datetime">2009/03/16 16:55:04 UTC</created_at>
            <accepted_at type="datetime">2009/03/19 19:00:00 UTC</accepted_at>
          </story>
          <story>
            <id type="integer">1</id>
            <project_id type=\"integer\">1</project_id>
            <story_type>feature</story_type>
            <url>$STORY_URL</url>
            <estimate type="integer">2</estimate>
            <current_state>accepted</current_state>
            <description>Windoze Save Dialog thingy</description>
            <name>The Save Dialog 2</name>
            <requested_by>Dana Deer</requested_by>
            <owned_by>Rob</owned_by>
            <created_at type="datetime">2009/03/16 16:55:04 UTC</created_at>
            <accepted_at type="datetime">2009/03/19 19:00:00 UTC</accepted_at>
          </story>
        </stories>
      </iteration>
      <iteration>
        <id type="integer">2</id>
        <number type="integer">1</number>
        <start type="datetime">2009/03/16 00:00:00 UTC</start>
        <finish type="datetime">2009/03/23 00:00:00 UTC</finish>
        <team_strength type="float">0.75</team_strength>
        <stories type="array">
          <story>
            <id type="integer">2</id>
            <project_id type=\"integer\">1</project_id>
            <story_type>feature</story_type>
            <url>$STORY_URL</url>
            <estimate type="integer">2</estimate>
            <current_state>accepted</current_state>
            <description>Windoze Save Dialog thingy</description>
            <name>The Save Dialog 1</name>
            <requested_by>Dana Deer</requested_by>
            <owned_by>Rob</owned_by>
            <created_at type="datetime">2009/03/16 16:55:04 UTC</created_at>
            <accepted_at type="datetime">2009/03/19 19:00:00 UTC</accepted_at>
          </story>
          <story>
            <id type="integer">3</id>
            <project_id type=\"integer\">1</project_id>
            <story_type>feature</story_type>
            <url>$STORY_URL</url>
            <estimate type="integer">2</estimate>
            <current_state>accepted</current_state>
            <description>Windoze Save Dialog thingy</description>
            <name>The Save Dialog 2</name>
            <requested_by>Dana Deer</requested_by>
            <owned_by>Rob</owned_by>
            <created_at type="datetime">2009/03/16 16:55:04 UTC</created_at>
            <accepted_at type="datetime">2009/03/19 19:00:00 UTC</accepted_at>
          </story>
        </stories>
      </iteration>
    </iterations>"""
        
    def test_getStories_SINGLE_BLOCK(self, APICall):
        # setup
        block = 'current'
        APICall.return_value = self.iterations_reponse
        
        # action
        stories = pt_api.getStories(self.project_id, block, self.token)
        
        # confirm
        self.assertEqual(stories[0].id, 0)
        self.assertEqual(stories[1].id, 1)
        
    def test_getStories_MULTI_BLOCK(self, APICall):
        # setup
        block = 'backlog'
        APICall.return_value = self.iterations_reponse
        
        # action
        stories = pt_api.getStories(self.project_id, block, self.token)
        
        # confirm
        self.assertEqual(stories[0][0].id, 0)
        self.assertEqual(stories[0][1].id, 1)
        self.assertEqual(stories[1][0].id, 2)
        self.assertEqual(stories[1][1].id, 3)

    def test_getStories_Unknown_Block(self, APICall):
        # setup
        block = 'UNKOWN_BLOCK'
        
        # action / confirm
        self.assertRaises(ValueError, pt_api.getStories, self.project_id, block, self.token)
