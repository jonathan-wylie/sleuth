from mock import patch, MagicMock
import datetime
import unittest2

from sleuth import pt_api


class Test_StorySearch(unittest2.TestCase):

    def test_init(self):
        # setup
        project_id = MagicMock()
        story_filter = MagicMock()

        # action
        story_search = pt_api.StorySearch(project_id, story_filter=story_filter)

        # confirm
        self.assertEqual(story_search.project_id, project_id)
        self.assertEqual(story_search.story_filter, story_filter)

    @patch('sleuth.pt_api.urllib')
    def test_url(self, urllib):
        # setup
        project_id = 4
        story_filter = MagicMock()
        encoded_args = 'filter=encoded_args'
        urllib.urlencode.return_value = encoded_args

        # action
        story_search = pt_api.StorySearch(project_id, story_filter=story_filter)

        # confirm
        self.assertEqual(story_search.url, 'https://www.pivotaltracker.com/services/v3/projects/%s/stories?%s' % (project_id, encoded_args))

    @patch('sleuth.pt_api.APICall')
    def test_get(self, APICall):
        # setup
        expected_data = 'XML From Pivotal Tracker'
        APICall.return_value = expected_data
        project_id = 5
        story_filter = 'some_filter'
        token = '__token__'
        story_search = pt_api.StorySearch(project_id, story_filter=story_filter)

        # action
        data = story_search.get(token)

        # confirm
        self.assertEqual(expected_data, data)
        APICall.assert_called_once_with(story_search.url, token)

    def test_filter_by_states_first_filter(self):
        # setup
        project_id = 4
        story_search = pt_api.StorySearch(project_id)

        # action
        story_search = story_search.filter_by_states(['state1', 'state2'])

        # confirm
        self.assertEqual(story_search.url, 'https://www.pivotaltracker.com/services/v3/projects/%s/stories?%s' % (project_id, 'filter=state%3Astate1%2Cstate2'))

    def test_filter_by_states_second_filter(self):
        # setup
        project_id = 4
        story_search = pt_api.StorySearch(project_id)

        # action
        story_search = story_search.filter_by_states(['state1', 'state2']).filter_by_states(['state3', 'state4'])

        # confirm
        self.assertEqual(story_search.url, 'https://www.pivotaltracker.com/services/v3/projects/%s/stories?%s' % (project_id, 'filter=state%3Astate1%2Cstate2+state%3Astate3%2Cstate4'))


class Test_APICall(unittest2.TestCase):

    @patch('sleuth.pt_api.subprocess')
    def test_APICall(self, subprocess):
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
class Test_get_stories(unittest2.TestCase):

    def setUp(self):
        self.token = 'xxxxxxxxxx'
        self.project_id = 1
        self.iterations_reponse = '''<?xml version="1.0" encoding="UTF-8"?>
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
    </iterations>'''
        self.ice_box_response = '''<stories type="array">
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
        </stories>'''

    def test_get_stories(self, APICall):
        # setup
        block = 'backlog'
        APICall.return_value = self.iterations_reponse

        # action
        stories = pt_api.get_stories(self.project_id, block, self.token)

        # confirm
        self.assertEqual(stories[0][0].id, 0)
        self.assertEqual(stories[0][1].id, 1)
        self.assertEqual(stories[1][0].id, 2)
        self.assertEqual(stories[1][1].id, 3)

    def test_get_stories_Unknown_Block(self, APICall):
        # setup
        block = 'UNKOWN_BLOCK'

        # action / confirm
        self.assertRaises(ValueError, pt_api.get_stories, self.project_id, block, self.token)

    def test_get_stories_icebox(self, APICall):
        # setup
        block = 'icebox'
        APICall.return_value = self.ice_box_response

        # action
        stories = pt_api.get_stories(self.project_id, block, self.token)

        # confirm
        self.assertEqual(stories[0][0].id, 0)
        self.assertEqual(stories[0][1].id, 1)


@patch('sleuth.pt_api.APICall')
@patch('sleuth.pt_api.objectify')
class Test_get_project_activities(unittest2.TestCase):

    def test(self, objectify, APICall):
        # setup
        project_id = 1
        since = datetime.datetime(2013, 8, 7, 20, 33, 30)
        token = '--token--'

        # action
        activitiesxml = pt_api.get_project_activities(project_id, since, token)

        # confirm
        APICall.assert_called_once_with('https://www.pivotaltracker.com/services/v4/projects/1/activities?occurred_since_date=2013/8/07%0020:33:30%20GMT',
                                        '--token--')
        self.assertEqual(activitiesxml, objectify.return_value)


@patch('sleuth.pt_api.APICall')
@patch('sleuth.pt_api.objectify')
class Test_get_project_activities_v3(unittest2.TestCase):

    def test(self, objectify, APICall):
        # setup
        project_id = 1
        since = datetime.datetime(2013, 8, 7, 20, 33, 30)
        token = '--token--'

        # action
        activitiesxml = pt_api.get_project_activities_v3(project_id, since, token)

        # confirm
        APICall.assert_called_once_with('https://www.pivotaltracker.com/services/v3/projects/1/activities?occurred_since_date=2013/8/07%0020:33:30%20GMT',
                                        '--token--')
        self.assertEqual(activitiesxml, objectify.return_value)


@patch('sleuth.pt_api.lxml.etree.tostring')
class Test_to_str(unittest2.TestCase):

    def test(self, tostring):
        # setup
        thing_to_str = MagicMock()

        # action
        thing_stringed = pt_api.to_str(thing_to_str)

        # confirm
        tostring.assert_called_once_with(thing_to_str)
        self.assertEqual(tostring.return_value, thing_stringed)


@patch('sleuth.pt_api.lxml_objectify')
@patch('sleuth.pt_api.logger')
class Test_objectify(unittest2.TestCase):
    
    def test_ok(self, logger, lxml_objectify):
        # action
        objectified = pt_api.objectify(MagicMock())
        
        # confirm
        self.assertEqual(lxml_objectify.fromstring.return_value, objectified)

    def test_fail(self, logger, lxml_objectify):
        # setup
        lxml_objectify.fromstring.side_effect = Exception
        
        # action
        objectified = pt_api.objectify(MagicMock())
        
        # confirm
        self.assertIsNone(objectified)
