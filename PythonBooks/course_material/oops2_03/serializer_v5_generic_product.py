import json
import xml.etree.ElementTree as et
from dataclasses import dataclass


@dataclass
class Song:
    song_id: str
    title: str
    artist: str

    # method to pass song properties to serializer
    def use_product(self, product):
        product.start_object("song", self.song_id)
        product.add_property("title", self.title)
        product.add_property("artist", self.artist)


def serialize(object_to_serialize, data_format):
    serializer_product = _get_serializer(data_format)
    # creator _get_serializer() returns a product class object
    # song is replaced by object_to_serialize as first positional argument
    # but is no longer passed to serializer_product()
    # for product class instantiation
    # as product classes no longer take that argument
    my_product = serializer_product()
    # use_product() instance method of
    # song / object_to_serialize class is called
    # to serialize the object using the appropriate
    # serializer, but the client doesn't need to know
    # which one that is!
    object_to_serialize.use_product(my_product)
    return str(my_product)


# Creator
# -------
def _get_serializer(data_format):
    if data_format == "JSON":
        return _JSONSerializer
    elif data_format == "XML":
        return _XMLSerializer
    else:
        raise ValueError(data_format)


# Product classes
# ---------------


# product 1 as a more generic class
# to accept any serializeable object
# not just song
class _JSONSerializer:
    # __init__() no longer requires object
    def __init__(self):
        self._current_object = None

    # use dictionary for JSON serializer
    # note: object_name not used, but interface
    # implementation expects 2 positional arguments
    # client doesn't need to know that for JSON
    # that argument is not used
    def start_object(self, object_name, object_id):
        self._current_object = {"id": object_id}

    # add object-specific properties
    def add_property(self, name, value):
        self._current_object[name] = value

    def __str__(self):
        return json.dumps(self._current_object)


# product 2 as a more generic class
# to accept any serializeable object
# not just song
class _XMLSerializer:
    # __init__() no longer requires object
    def __init__(self):
        self._element = None

    # use XML structure
    def start_object(self, object_name, object_id):
        self._element = et.Element(object_name, attrib={"id": object_id})

    def add_property(self, name, value):
        prop = et.SubElement(self._element, name)
        prop.text = value

    def __str__(self):
        return et.tostring(self._element, encoding="unicode")