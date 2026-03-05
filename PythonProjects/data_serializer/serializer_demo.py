class Song:
    def __init__(self, title, artist, duration):
        self.title = title
        self.artist = artist
        self.id = id

    def __str__(self):
        return f"{self.title} by {self.artist} ({self.id} seconds)"
    
def serialize_song(song, data_format):
    if data_format == "json":
        import json
        return json.dumps({
            "title": song.title,
            "artist": song.artist,
            "id": song.id
        })
    elif data_format == "xml":
        import xml.etree.ElementTree as ET
        root = ET.Element("song")
        title = ET.SubElement(root, "title")
        title.text = song.title
        artist = ET.SubElement(root, "artist")
        artist.text = song.artist
        id = ET.SubElement(root, "id")
        id.text = str(song.id)
        return ET.tostring(root, encoding="unicode")
    else:
        raise ValueError("Unsupported data format")
    
# TODO : Create creator function for Song class and use it to create a song object and product to serialize it in both json and xml formats.
# TODO create a class for creator and product and use it to create a song object and product to serialize it in both json and xml formats.