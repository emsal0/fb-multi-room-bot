#!/usr/bin/env python

import fbchat
import os
import traceback
import logging
import sys

def array_safe_get(arr, index):
    try:
        return arr[index]
    except IndexError:
        return None

## This is a cool bot
class CubeBot(fbchat.Client):

    admin_only_commands = {'addroom'}

    def __init__(self,email, password, debug=True, user_agent=None, admin_ids=None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        if admin_ids is None:
            self.admin_ids = []
        self.admin_ids = admin_ids

        fbchat.Client.__init__(self,email, password, debug, user_agent)
        self.room_groups = []

    @staticmethod
    def get_room_for_reply(metadata):
        """
        From message metadata, extract two values: the id to send back to, and whether or not the id is a user.
        """
        try:
            threadKey = metadata['delta']['messageMetadata']['threadKey']
            if 'otherUserFbId' in threadKey:
                return (threadKey['otherUserFbId'], True)
            elif 'threadFbId' in threadKey:
                return (threadKey['threadFbId'], False)
        except:
            raise

    def roomlist_to_str(self):
        room_group_card = len(self.room_groups)
        roomstrings = ["{i}: {s}".format(i=i, s=self.room_groups[i]) for i in range(room_group_card)]
        if len(roomstrings) == 0:
            return "No room lists here! Tell the bot admin to add some."
        return '\n'.join(roomstrings)

    def echo_message(self, author_id, entity_id, message, metadata, is_user=True):

        if str(author_id) != str(self.uid):
            attachment_ids = []

            if 'attachments' in metadata['delta']:
                attachment_ids = [attachment['id'] for attachment in metadata['delta']['attachments']]

            self.send(entity_id, message, is_user, image_id=array_safe_get(attachment_ids,0))

            for attachment_id in attachment_ids[1:]:
                self.send(entity_id, "", is_user, image_id=attachment_id)

    def add_room_group(self, author_id, room_id, group_to_join=None):
        self.logger.info("add to room group {}".format(group_to_join))
        if room_id is None:
            return

        if group_to_join is not None:
            try:
                self.room_groups[int(group_to_join)].update({room_id})
            except IndexError:
                pass
            except:
                raise
            return

        self.room_groups.append({room_id})

    def list_rooms(self, roomid, is_user):
        self.send(roomid, self.roomlist_to_str(), is_user) 

    def parse_message(self, author_id, message, metadata, replyid, is_user):
        if not message.startswith('!'):
            real_author_name = self.getUserInfo(author_id)['name']

            for group in self.room_groups:
                if replyid in group:
                    for room in group - {replyid}:
                        self.echo_message(author_id, room,
                            "{} said:\n{}".format(real_author_name, message), metadata, is_user)


        fields = message[1:].split(" ")

        if fields[0] in CubeBot.admin_only_commands and author_id not in self.admin_ids:
            return

        elif fields[0] == "addroom":
            self.add_room_group(author_id, array_safe_get(fields, 1), array_safe_get(fields, 2))
        elif fields[0] == "getrooms":
            self.list_rooms(replyid, is_user)

    def on_message(self, mid, author_id, author_name, message, metadata):
        self.logger.debug("==========================================")
        self.logger.debug("{}: {}".format(author_id, message))
        self.logger.debug("metadata: {}".format(metadata))


        self.markAsDelivered(author_id, mid) #mark delivered
        self.markAsRead(author_id) #mark read

        replyid, is_user = CubeBot.get_room_for_reply(metadata)

        self.parse_message(author_id, message, metadata, replyid, is_user)

if __name__ == "__main__":

    admins = os.environ["BOT_ADMINS"].split(" ")
    logging.basicConfig(stream=sys.stdout)
    logging.getLogger("client").setLevel(logging.CRITICAL)

    bot = CubeBot(os.environ["BOT_USERNAME"], os.environ["BOT_PASSWORD"], admin_ids=admins, debug=False)
    bot.listen()
