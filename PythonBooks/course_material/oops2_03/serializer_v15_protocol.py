from abc import ABC, abstractmethod
from dataclasses import dataclass

# import Protocol
from typing import Protocol

import json
import xml.etree.ElementTree as et
import yaml

# Client Object classes
# ---------------------


class ClientObjectBluePrint(ABC):
    @abstractmethod
    def use_product(self):
        pass


@dataclass
class Song(ClientObjectBluePrint):
    song_id: str
    title: str
    artist: str

    def use_product(self, product):
        product.start_object("song", self.song_id)
        product.add_property("title", self.title)
        product.add_property("artist", self.artist)


@dataclass
class Book(ClientObjectBluePrint):
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
    my_product = creator.factory_method(data_format)
    object_to_serialize.use_product(my_product)
    print(creator)
    return str(my_product)


# Creator classes
# ---------------


class CreatorBluePrint(ABC):
    @abstractmethod
    def factory_method(self):
        pass

    @abstractmethod
    def register_format(self):
        pass


class SerializerCreator(CreatorBluePrint):
    def __init__(self):
        self._products = dict()
        self.data_format = None

    def register_format(self, data_format, product):
        self._products[data_format] = product

    def factory_method(self, data_format):
        self.data_format = data_format
        product = self._products.get(data_format)
        if not product:
            raise ValueError(data_format)
        return product()

    def __repr__(self):
        return f"Your Creator today: SerializerCreator"

    def __str__(self):
        return f"""
        Dear Client,

        Thank you for your purchase of:
        Serializer: {self.data_format}

        {self.__repr__()}

        Your product is below:                
        """


# Product classes
# ---------------


# Protocol instead of ABC
class SerializationProduct(Protocol):
    def start_object(self, object_name: str, object_id: int) -> None: ...

    def add_property(self) -> None: ...

    def __str__(self) -> str: ...


class _JSONSerializer:
    def __init__(self):
        # dictionary instead of None
        self._current_object = dict()

    # use .add_property() to populate
    def start_object(self, object_name, object_id):
        self.add_property("id", object_id)

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


class _YAMLSerializer(_JSONSerializer):
    def __str__(self):
        return yaml.dump(self._current_object)

# Register
creator = SerializerCreator()
creator.register_format("JSON", _JSONSerializer)
creator.register_format("XML", _XMLSerializer)
creator.register_format("YAML", _YAMLSerializer)