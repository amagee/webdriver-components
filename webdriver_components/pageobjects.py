import functools
from webdriver_components.utils import (retry_until_successful, retry_until_true, set_element_text,
    get_element, get_elements, ElementNotFound, MultipleElementsReturned)
from collections.abc import Iterable


class PathItem:
    def __init__(self, factory=None):
        self.factory = factory


class Css(PathItem):
    def __init__(self, css_selector, multiple=False, **kwargs):
        super(Css, self).__init__(**kwargs)
        self.css_selector = css_selector
        self.multiple = multiple

    def __str__(self):
        if self.factory is not None:
            s = "{}(css={})".format(self.factory().__name__, self.css_selector)
        else:
            s = "[css={}]".format(self.css_selector)
        if self.multiple:
            s += "*"
        return s

    def get_element(self, el):
        if self.multiple:
            el = get_elements(el, css=self.css_selector)
        else:
            el = get_element(el, css=self.css_selector)
        return el

    def __eq__(self, other):
        return isinstance(other, Css) and other.css_selector == self.css_selector and other.multiple == self.multiple


class IndexPathItem(PathItem):
    def __init__(self, index, **kwargs):
        super(IndexPathItem, self).__init__(**kwargs)
        self.index = index

    def __str__(self):
        if self.factory is not None:
            s = "{}(index={})".format(self.factory().__name__, self.index)
        else:
            s = "[index={}]".format(self.index)
        return s

    def get_element(self, el):
        el = el[self.index]
        if self.factory is not None:
            el = self.factory()(driver=None, path=None, el=el)
        return el

    def __eq__(self, other):
        return isinstance(other, IndexPathItem) and other.index == self.index


class ComponentMetaclass(type):
    def __new__(cls, name, bases, attrs):
        def process_item(item):
            if isinstance(item, PathItem):
                def prop(self):
                    if item.multiple and item.factory:
                        klass = make_component_list_class(item.factory())
                    elif item.multiple:
                        klass = make_component_list_class(Component)
                    elif item.factory:
                        klass = item.factory()
                    else:
                        klass = Component
                    return klass(self.driver, [*self.path, item])
                return property(functools.partial(prop))
            else:
                return item

        attrs = {k: process_item(v) for k, v in attrs.items()}
        return super(ComponentMetaclass, cls).__new__(cls, name, bases, attrs)



class PathNotFound(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return f"Couldn't find path {'/'.join([str(p) for p in self.path])}"


class PathHadMultipleElements(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return f"Unexpected multiple elements for path {'/'.join([str(p) for p in self.path])}"


class ComponentMixin:
    def _get_el(self):
        try:
            el = self.driver
            for p in self.path:
                el = p.get_element(el)
            return el
        except ElementNotFound:
            raise PathNotFound(self.path)
        except MultipleElementsReturned:
            raise PathHadMultipleElements(self.path)

    def get_el(self, **kwargs):
        el = None
        def get():
            nonlocal el
            el = self._get_el()
            return (el is not None)
        self.retry_until_true(get, **kwargs)
        return el

    def retry_until_successful(self, func, **kwargs):
        if hasattr(self.driver, 'poller'):
            self.driver.poller.retry_until_successful(func, **kwargs)
        else:
            retry_until_successful(func, **kwargs)

    def retry_until_true(self, func, **kwargs):
        if hasattr(self.driver, 'poller'):
            self.driver.poller.retry_until_true(func, **kwargs)
        else:
            retry_until_true(func, **kwargs)

    def exists(self, **kwargs):
        try:
            self._get_el(**({k: v for k, v in kwargs.items() if k != 'timeout_ms'}))
        except PathNotFound:
            return False
        else:
            return True

    def does_not_exist(self, **kwargs):
        return not self.exists(**kwargs)

    @property
    def is_checked(self):
        return self.get_el().get_attribute('checked') == 'true'

    def set_checkbox_value(self, is_checked):
        if self.is_checked != is_checked:
            self.get_el().click()



class Component(ComponentMixin, metaclass=ComponentMetaclass):
    def __init__(self, driver, path=None):
        self.driver = driver
        self.path = path or []

    def get(self, selector, multiple=False):
        """
        Return an ElementQuery based on the selector. All the following are equivalent: 

        - self.get([Css(".mychild")])
        - self.get(Css(".mychild"))
        - self.get(".mychild")
        """
        if isinstance(selector, str):
            selector = [Css(selector, multiple=multiple)]
        elif not isinstance(selector, Iterable):
            selector = [selector]

        if selector[-1].multiple:
            klass = make_component_list_class(Component)
        else:
            klass = Component
        return klass(self.driver, [*self.path, *selector])

    def set_text(self, text, expected_text=None, defocus=False):
        """
        Note that this is more advanced than WebElement's send_keys in that it
        will clear existing text from the text box if there is any.
        """
        return set_element_text(self.get_el(),
            text, 
            expected_text=expected_text, 
            defocus=defocus
        )

    def click(self, **kwargs):
        self.retry_until_successful(lambda: self.get_el().click(), **kwargs)

    @property
    def text(self):
        return self.get_el().text

    @property
    def value(self):
        return self.get_el().get_attribute('value')



def make_component_list_class(klass):
    class ComponentList(ComponentMixin):
        def __init__(self, driver, path=None):
            self.driver = driver
            self.path = path or []

        def __getitem__(self, index):
            return klass(self.driver, [*self.path, IndexPathItem(index)])

        def __iter__(self):
            def generator():
                length = len(self.get_el())
                for i in range(0, length):
                    yield self[i]
            return iter(generator())

        def __len__(self):
            return len(self.get_el())
    return ComponentList


