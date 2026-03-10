import json
import xml.etree.ElementTree as et


class Song:
    def __init__(self, song_id, title, artist):
        self.song_id = song_id
        self.title = title
        self.artist = artist


# move serializing functionality into products
def serialize(song, data_format):
    if data_format == "JSON":
        # call _serialize_to_json
        _serialize_to_json(song)
    elif data_format == "XML":
        # call _serialize_to_xml
        _serialize_to_xml(song)
    else:
        raise ValueError(data_format)


# Products
# --------
def _serialize_to_json(song):
    song_info = {"id": song.song_id, "title": song.title, "artist": song.artist}
    return json.dumps(song_info)


def _serialize_to_xml(song):
    song_info = et.Element("song", attrib={"id": song.song_id})
    title = et.SubElement(song_info, "title")
    title.text = song.title
    artist = et.SubElement(song_info, "artist")
    artist.text = song.artist
    return et.tostring(song_info, encoding="unicode")
