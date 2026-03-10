import json
import xml.etree.ElementTree as et
from dataclasses import dataclass


@dataclass
class Song:
    song_id: str
    title: str
    artist: str

    def use_product(self, product):
        product.start_object("song", self.song_id)
        product.add_property("title", self.title)
        product.add_property("artist", self.artist)


@dataclass
class Book:
    book_id: str
    title: str
    author: str
    publisher: str

    def use_product(self, product):
        product.start_object("book", self.book_id)
        product.add_property("title", self.title)
        product.add_property("author", self.author)
        product.add_property("publisher", self.publisher)


def serialize(object_to_serialize, data_format):
    # instantiate creator class
    creator = SerializerCreator()
    my_product = creator.get_serializer(data_format)
    object_to_serialize.use_product(my_product)
    return str(my_product)


# Creator as class
# ----------------
class SerializerCreator:
    # public static method
    @staticmethod
    def get_serializer(data_format):
        if data_format == "JSON":
            return _JSONSerializer()
        elif data_format == "XML":
            return _XMLSerializer()
        else:
            raise ValueError(data_format)


# Product classes
# ---------------
class _JSONSerializer:
    def __init__(self):
        self._current_object = None

    def start_object(self, object_name, object_id):
        self._current_object = {"id": object_id}

    def add_property(self, name, value):
        self._current_object[name] = value

    def __str__(self):
        return json.dumps(self._current_object)


class _XMLSerializer:
    def __init__(self):
        self._element = None

    def start_object(self, object_name, object_id):
        self._element = et.Element(object_name, attrib={"id": object_id})

    def add_property(self, name, value):
        prop = et.SubElement(self._element, name)
        prop.text = value

    def __str__(self):
        return et.tostring(self._element, encoding="unicode")