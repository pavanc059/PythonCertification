import json
import xml.etree.ElementTree as et


class Song:
    def __init__(self, song_id, title, artist):
        self.song_id = song_id
        self.title = title
        self.artist = artist


def serialize(song, data_format):
    if data_format == "JSON":
        song_info = {"id": song.song_id, "title": song.title, "artist": song.artist}
        return json.dumps(song_info)
    elif data_format == "XML":
        song_info = et.Element("song", attrib={"id": song.song_id})
        title = et.SubElement(song_info, "title")
        title.text = song.title
        artist = et.SubElement(song_info, "artist")
        artist.text = song.artist
        return et.tostring(song_info, encoding="unicode")
    else:
        raise ValueError(data_format)
