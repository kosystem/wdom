#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from collections import Iterable
from typing import Tuple, Union

from wdom.node import Node
from wdom.element import DOMTokenList, ElementMeta
from wdom.element import (
    HTMLIFrameElement, HTMLInputElement, HTMLOptionElement, HTMLSelectElement,
    HTMLScriptElement, HTMLTextAreaElement,
)
from wdom.web_node import WebElement

logger = logging.getLogger(__name__)


class HTMLElement(WebElement):
    pass


class TagBaseMeta(ElementMeta):
    '''Meta class to set default class variable of HtmlDom'''
    def __prepare__(name, bases, **kwargs) -> dict:
        return {'inherit_class': True}


class Tag(HTMLElement, metaclass=TagBaseMeta):
    '''Base class for html tags. ``HTMLElement`` requires to specify tag name
    when instanciate it, but this class and sublasses have default tag name and
    not need to specify it for each thier instances.

    Additionally, this class provides shortcut properties to handle some
    special attributes (class, type, is).
    '''
    #: Tag name used for this node.
    tag = 'tag'
    #: str and list of strs are acceptale.
    class_ = ''
    #: Inherit classes defined in super class or not.
    #: By default, this variable is True.
    inherit_class = True
    #: use for <input> tag's type
    type_ = ''
    #: custom element which extends built-in tag (like <table is="your-tag">)
    is_ = ''

    def __init__(self, *args, attrs=None, **kwargs):
        if attrs:
            kwargs.update(attrs)
        if self.type_ and 'type' not in kwargs:
            kwargs['type'] = self.type_
        if self.is_ and 'is' not in kwargs and 'is_' not in kwargs:
            kwargs['is'] = self.is_
        super().__init__(self.tag, **kwargs)
        self.append(*args)

    @classmethod
    def get_class_list(cls) -> DOMTokenList:
        '''Return class-level class list, including all super class's.
        '''
        l = []
        l.append(DOMTokenList(cls, cls.class_))
        if cls.inherit_class:
            for base_cls in cls.__bases__:
                if issubclass(base_cls, Tag):
                    l.append(base_cls.get_class_list())
        # Reverse order so that parent's class comes to front
        l.reverse()
        return DOMTokenList(cls, l)

    def __getitem__(self, attr: Union[str, int]) -> Union[Node, str]:
        if isinstance(attr, int):
            return self.childNodes[attr]
        else:
            return self.getAttribute(attr)

    def __setitem__(self, attr: str, val):
        self.setAttribute(attr, val)

    def __delitem__(self, attr: str):
        self.removeAttribute(attr)

    def __copy__(self) -> HTMLElement:
        clone = type(self)()
        for attr in self.attributes:
            clone.setAttribute(attr, self.getAttribute(attr))
        for c in self.classList:
            clone.addClass(c)
        return clone

    def getAttribute(self, attr:str) -> str:
        if attr == 'class':
            cls = self.get_class_list()
            cls._append(self.classList)
            if cls:
                return cls.toString()
            else:
                return None
        else:
            return super().getAttribute(attr)

    def addClass(self, *classes:Tuple[str]):
        self.classList.add(*classes)

    def hasClass(self, class_: str) -> bool:
        return class_ in self.classList

    def hasClasses(self) -> bool:
        return len(self.classList) > 0

    def removeClass(self, *classes:Tuple[str]):
        _remove_cl = []
        for class_ in classes:
            if class_ not in self.classList:
                if class_ in self.__class__.get_class_list():
                    logger.warning(
                        'tried to remove class-level class: '
                        '{}'.format(class_)
                    )
                else:
                    logger.warning(
                        'tried to remove non-existing class: {}'.format(class_)
                    )
            else:
                _remove_cl.append(class_)
        self.classList.remove(*_remove_cl)

    def show(self):
        self.hidden = False

    def hide(self):
        self.hidden = True

    @property
    def type(self) -> str:
        return self.getAttribute('type') or self.type_

    @type.setter
    def type(self, val:str):
        self.setAttribute('type', val)


class NestedTag(Tag):
    #: Inner nested tag class
    inner_tag_class = None
    def __init__(self, *args, **kwargs):
        self._inner_element = None
        super().__init__(**kwargs)
        if self.inner_tag_class:
            self._inner_element = self.inner_tag_class()
            super().appendChild(self._inner_element)
        self.append(*args)

    def appendChild(self, child) -> Node:
        if self._inner_element:
            return self._inner_element.appendChild(child)
        else:
            return super().appendChild(child)

    def insertBefore(self, child: Node, ref_node: Node) -> Node:
        if self._inner_element:
            return self._inner_element.insertBefore(child, ref_node)
        else:
            return super().insertBefore(child, ref_node)

    def removeChild(self, child:Node) -> Node:
        if self._inner_element:
            return self._inner_element.removeChild(child)
        else:
            return super().removeChild(child)

    def replaceChild(self, new_child: Node, old_child: Node) -> Node:
        if self._inner_element:
            return self._inner_element.replaceChild(new_child, old_child)
        else:
            return super().replaceChild(new_child, old_child)

    @property
    def childNodes(self):
        if self._inner_element:
            return self._inner_element.childNodes
        else:
            return super().childNodes

    def empty(self):
        if self._inner_element:
            self._inner_element.empty()
        else:
            super().empty()

    @property
    def textContent(self) -> str:
        return super().textContent

    @textContent.setter
    def textContent(self, text:str):
        if self._inner_element:
            self._inner_element.textContent = text
        else:
            # Need a trick to call property of super-class
            Tag.textContent.fset(self, text)

    @property
    def html(self) -> str:
        if self._inner_element:
            return self.start_tag + self._inner_element.html + self.end_tag
        else:
            return Tag.html.fget(self)

    @property
    def innerHTML(self) -> str:
        if self._inner_element:
            return self._inner_element.innerHTML
        else:
            return Tag.innerHTML.fget(self)

    @innerHTML.setter
    def innerHTML(self, html:str):
        if self._inner_element:
            self._inner_element.innerHTML = html
        else:
            Tag.innerHTML.fset(self, html)


def NewTagClass(class_name: str, tag: str=None, bases: Tuple[type]=(Tag, ),
                 **attrs) -> type:
    '''Generate and return new ``Tag`` class. If ``tag`` is empty, lower case
    of ``class_name`` is used for a tag name of the new class. ``bases`` should
    be a tuple of base classes. If it is empty, use ``Tag`` class for a base
    class. Other keyword arguments are used for class variables of the new
    class.

    Example::

        MyButton = NewTagClass(
                        'MyButton', 'button', (Button,), class_='btn')
        my_button = MyButton('Click!')
        print(my_button.html)

        >>> <button class="btn" id="111111111">Click!</button>
    '''
    if tag is None:
        tag = class_name.lower()
    if type(bases) is not tuple:
        if isinstance(bases, Iterable):
            bases = tuple(bases)
        elif isinstance(bases, type):
            bases = (bases, )
        else:
            TypeError('Invalid base class: {}'.format(str(bases)))
    cls = type(class_name, bases, attrs)
    cls.tag = tag
    return cls


class Input(Tag, HTMLInputElement):
    '''Base class for ``<input>`` element.
    '''
    tag = 'input'
    #: type attribute; text, button, checkbox, or radio... and so on.
    type_ = ''

    def __init__(self, *args, **kwargs) -> None:
        if self.type_ and 'type' not in kwargs:
            kwargs['type'] = self.type_
        super().__init__(*args, **kwargs)


class Textarea(Tag, HTMLTextAreaElement):
    '''Base class for ``<textarea>`` element.'''
    tag = 'textarea'

    @property
    def value(self) -> str:
        '''Get input value of this node. This value is used as a default value
        of this element.
        '''
        return self.textContent

    @value.setter
    def value(self, value: str) -> None:
        self.textContent = value


class Script(Tag, HTMLScriptElement):
    tag = 'script'

    def __init__(self, *args, type='text/javascript', **kwargs):
        super().__init__(*args, type=type, **kwargs)


Html = NewTagClass('Html')
Body = NewTagClass('Body')
Meta = NewTagClass('Meta')
Head = NewTagClass('Head')
Link = NewTagClass('Link')
Title = NewTagClass('Title')
Style = NewTagClass('Style')
Iframe = NewTagClass('Iframe', 'iframe', (Tag, HTMLIFrameElement))

Div = NewTagClass('Div')
Span = NewTagClass('Span')

# Typography
H1 = NewTagClass('H1')
H2 = NewTagClass('H2')
H3 = NewTagClass('H3')
H4 = NewTagClass('H4')
H5 = NewTagClass('H5')
H6 = NewTagClass('H6')

P = NewTagClass('P')
A = NewTagClass('A')
Strong = NewTagClass('Strong')
Em = NewTagClass('Em')
U = NewTagClass('U')
Br = NewTagClass('Br')
Hr = NewTagClass('Hr')

Cite = NewTagClass('Cite')
Code = NewTagClass('Code')
Pre = NewTagClass('Pre')

Img = NewTagClass('Img')

# table tags
Table = NewTagClass('Table')
Thead = NewTagClass('Thead')
Tbody = NewTagClass('Tbody')
Tfoot = NewTagClass('Tfoot')
Th = NewTagClass('Th')
Tr = NewTagClass('Tr')
Td = NewTagClass('Td')

# List tags
Ol = NewTagClass('Ol')
Ul = NewTagClass('Ul')
Li = NewTagClass('Li')

# Definition-list tags
Dl = NewTagClass('Dl')
Dt = NewTagClass('Dt')
Dd = NewTagClass('Dd')

# Form tags
Form = NewTagClass('Form')
Button = NewTagClass('Button', 'button', Tag)
Label = NewTagClass('Label')
CheckBox = NewTagClass('CheckBox', 'input', Input, type_='checkbox')
TextInput = NewTagClass('TextInput', 'input', Input, type_='text')
Select = NewTagClass('Select', 'select', (NestedTag, HTMLSelectElement))
Option = NewTagClass('Option', 'option', (Tag, HTMLOptionElement))

# Building blocks
Container = Div
Wrapper = Div
Row = Div
FormGroup = Div
Col = Div
Col1 = Div
Col2 = Div
Col3 = Div
Col4 = Div
Col5 = Div
Col6 = Div
Col7 = Div
Col8 = Div
Col9 = Div
Col10 = Div
Col11 = Div
Col12 = Div

# Some css updates
DefaultButton = Button
PrimaryButton = Button
SuccessButton = Button
InfoButton = Button
WarningButton = Button
DangerButton = Button
LinkButton = Button

# css/js/headers
css_files = []
js_files = []
headers = []

default_classes = (
    Input,
    Textarea,
    Button,
    Script,
    Html,
    Body,
    Meta,
    Head,
    Link,
    Title,
    Style,
    Div,
    Span,
    H1,
    H2,
    H3,
    H4,
    H5,
    H6,
    P,
    A,
    Strong,
    Em,
    U,
    Br,
    Hr,
    Cite,
    Code,
    Pre,
    Img,
    Table,
    Thead,
    Tbody,
    Tfoot,
    Th,
    Tr,
    Td,
    Ol,
    Ul,
    Li,
    Dl,
    Dt,
    Dd,
    Form,
    Label,
    Option,
    Select,
)
