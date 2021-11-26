#!/usr/bin/env python3

import logging

logger = logging.getLogger(__name__)

class TagList():
    """Collection of tags."""

    def __init__(self):
        """Initialise instance variables."""
        self.__tags = []

    def expand_tagsets(self, tags_input, tagsets=None):
        """Expand tagsets  from a list of possible tagsets."""
        if not tagsets is None:
            # expand abbreviations entered by the user
            tags = []
            for part in tags_input:
                # if a non-empty array is returned the part of the user input was an
                # abbreviation
                # if no matching tagset is found treat the part as a new tag
                tagset = tagsets.get_tagset(part)
                if len(tagset) > 0:
                    logger.debug('extended abbreviation "{}" -> {}'.format(
                        part, ','.join(tagset)))
                    tags.extend(tagset)
                else:
                    tags.append(part)
            return tags
        else:
            return tags_input

    def toggle_tags(self, tags_input, tagsets=None, force_all=False,
        force="toggle"):
        """Toggle individual tags.

        Will expand tagsets first.
        Will by itself not write tags to any file.

        Expands nested tags so that if you set "tags|my tags|special tag"
        "tags" and "tags|my tags" will be set as well. On removal of
        "tags|my tags|special tag" it will check if "tags" or "tags|my tags" are
        used by other tags (e.g. "tags|your tags" or "tags|my tags|not special")
        and remove those tags as well if they are not needed.

        Positional arguments:
        tags -- List of tags

        Keyword arguments:
        force_all -- force the existence of all tags before removing all
        force -- do not toggle but force "in" / "out" or "toggle"
        """

        tags = self.expand_tagsets(tags_input, tagsets=tagsets)

        # filter duplicates & sort
        tags = list(set(tags))
        tags.sort()
        logger.info('toggle tags: {}'.format(','.join(tags)))

        # collect tags that were added / removed
        remove = []
        add = []

        if force_all:
            # if all items are already there
            if all(tag in tags for tag in self.__tags):
                # remove all
                for tag in tags:
                    remove += self._remove_from_taglist(tag)
            else:
                # add all
                for tag in tags:
                    add += self._add_to_taglist(tag)
        else:
            for tag in tags:
                if tag in self.__tags:
                    if not force == "in":
                        remove += self._remove_from_taglist(tag)
                else:
                    if not force == "out":
                        add += self._add_to_taglist(tag)

        return {'add': list(set(add)), 'remove': list(set(remove))}

    def get_tags(self):
        """Return a list of tags."""
        return self.__tags

    def load_tags(self, tags, intersect=False):
        """Load tags, for initial construction, else use toggle_tags.

        Will not add duplicate tags.
        Will by itself not write tags to any file.

        Positional arguments:
        tags -- list of tags to add

        Keyword arguments:
        intersect -- use only tags that are already present and in "tags"
        """
        if not intersect:
            for tag in tags:
                if not tag in self.__tags and not tag == '':
                    self.__tags.append(tag)
        else:
            keep = []
            for tag in tags:
                if tag in self.__tags and not tag == '':
                    keep.append(tag)
            self.__tags = keep

    def _remove_from_taglist(self, remove):
        """Recursively remove a tag and its parents if no other children exist.

        Return a List of tags that were removed.

        Positional arguments:
        remove -- the tag to remove
        """
        if not remove in self.__tags:
            return []

        # a child tag would begin with "tag|"
        child = remove + '|'

        # check if there is a child
        if any(tag.startswith(child) for tag in self.__tags):
            return []

        # if not remove it
        self.__tags.remove(remove)

        # return the tag as removed and try to remove its parent as well
        index = remove.rfind('|')
        if index > 0:
            # there's a parent
            return [remove] + self._remove_from_taglist(remove[0:index])
        else:
            return [remove]

    def _add_to_taglist(self, add):
        """Add a tag and its parents to the taglist.

        Positional arguments:
        add -- the tag to add
        """
        if add in self.__tags:
            return []

        self.__tags.append(add)

        # return the tag as added and try to add its parent as well
        index = add.rfind('|')
        if index > 0:
            # there's a parent
            return [add] + self._add_to_taglist(add[0:index])
        else:
            return [add]

