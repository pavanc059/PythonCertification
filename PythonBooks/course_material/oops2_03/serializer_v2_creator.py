import json
import xml.etree.ElementTree as et


class Song:
    def __init__(self, song_id, title, artist):
        self.song_id = song_id
        self.title = title
        self.artist = artist


def serialize(song, data_format):
    # move decision making to separate function
    # call creator _get_serializer
    _get_serializer(song, data_format)


# Creator
# -------
def _get_serializer(song, data_format):
    if data_format == "JSON":
        return _serialize_to_json(song)
    elif data_format == "XML":
        return _serialize_to_xml(song)
    else:
        raise ValueError(data_format)


# Products
# --------


# product 1
def _serialize_to_json(song):
    return json.dumps({"id": song.song_id, "title": song.title, "artist": song.artist})


# product 2
def _serialize_to_xml(song):
    song_info = et.Element("song", attrib={"id": song.song_id})
    title = et.SubElement(song_info, "title")
    title.text = song.title
    artist = et.SubElement(song_info, "artist")
    artist.text = song.artist
    return et.tostring(song_info, encoding="unicode")
