import json
import xml.etree.ElementTree as et


class Song:
    def __init__(self, song_id, title, artist):
        self.song_id = song_id
        self.title = title
        self.artist = artist


def serialize(song, data_format):
    # call creator get_serializer
    serializer = _get_serializer(data_format)
    # creator returns a function object
    # pass song to that function and execute
    return serializer(song)


# Creator
# -------
# remove song as positional argument
def _get_serializer(data_format):
    if data_format == "JSON":
        # return _serialize_to_json object
        return _serialize_to_json
    elif data_format == "XML":
        # return _serialize_to_xml object
        return _serialize_to_xml
    else:
        raise ValueError(data_format)


# Products
# --------


def _serialize_to_json(song):
    return json.dumps({"id": song.song_id, "title": song.title, "artist": song.artist})


def _serialize_to_xml(song):
    song_info = et.Element("song", attrib={"id": song.song_id})
    title = et.SubElement(song_info, "title")
    title.text = song.title
    artist = et.SubElement(song_info, "artist")
    artist.text = song.artist
    return et.tostring(song_info, encoding="unicode")