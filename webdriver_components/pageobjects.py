import functools
from webdriver_components.utils import (retry_until_successful, retry_until_true, set_element_text,
    get_element, get_elements, ElementNotFound)


class PathItem:
    def __init__(self, factory=None, query_methods=None):
        self.factory = factory
        self.query_methods = query_methods or {}


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


class CustomPathItem:
    def __init__(self, name, func, func_kwargs, **kwargs):
        super(CustomPathItem, self).__init__(**kwargs)
        self.name = name
        self.func = func
        self.kwargs = func_kwargs

    def __str__(self):
        return "[{}={}]".format(self.name, self.kwargs)

    def get_element(self, el):
        return self.func(el, **self.kwargs)


def path_item_to_property(path_item):
    if isinstance(path_item, PathItem):
        def getter(self):
            attrs = {}
            p1 = [*(self.path or []), path_item]
            if not path_item.multiple and path_item.factory is not None:
                attrs = {**attrs, **path_item.factory().__dict__}
                
            for query_method_name, query_method in path_item.query_methods.items():
                def method(self, query_method_name, query_method, **kwargs):
                    return ElementQuery(self.driver, [*p1, CustomPathItem(query_method_name, query_method, kwargs)])
                attrs[query_method_name] = (lambda query_method_name, query_method: (
                    lambda self, **kwargs: method(self, query_method_name, query_method, **kwargs)
                ))(query_method_name, query_method)

            return type('ElementQuery', (ElementQuery,), attrs)(self.driver, p1)
        return property(functools.partial(getter))
    else:
        return path_item



class ElementQueryMetaclass(type):
    def __new__(cls, name, bases, attrs):
        return super(ElementQueryMetaclass, cls).__new__(
            cls, 
            name, 
            bases, 
            {k: path_item_to_property(v) for k, v in attrs.items()}
        )


class ElementQuery(metaclass=ElementQueryMetaclass):
    def __init__(self, driver, path):
        self.driver = driver
        self.path = path

    def __str__(self):
        return "/".join([str(p) for p in self.path])

    def __getitem__(self, index):
        if self.path and self.path[-1].factory:
            klass = self.path[-1].factory()
        else:
            klass = ElementQuery

        return klass(self.driver, [
            *self.path,
            IndexPathItem(
                index, 
                factory=self.path[-1].factory if self.path else None
            )
        ])

    def __iter__(self):
        def generator():
            length = len(self.get_el())
            for i in range(0, length):
                yield self[i]
        return iter(generator())

    def __len__(self):
        return len(self.get_el())

    def _get_el(self):
        el = self.driver
        for p in self.path:
            el = p.get_element(el)
        return el

    def get_el(self, **kwargs):
        el = None
        def get():
            nonlocal el
            el = self._get_el()
            return (el is not None)
        self.retry_until_true(get, **kwargs)
        return el

    def get(self, selector, multiple=False):
        """
        Return an ElementQuery based on the selector. All the following are equivalent: 

        - self.get([Css(".mychild")])
        - self.get(Css(".mychild"))
        - self.get(".mychild")
        """
        if isinstance(selector, str):
            path = [Css(selector, multiple=multiple)]
        elif not isinstance(path, Iterable):
            path = [selector]
        return ElementQuery(self.driver, [*self.path, *path])

    def exists(self, **kwargs):
        try:
            self._get_el(**({k: v for k, v in kwargs.items() if k != 'timeout_ms'}))
        except ElementNotFound:
            return False
        else:
            return True

    def does_not_exist(self, **kwargs):
        return not self.exists(**kwargs)

    def click(self, **kwargs):
        self.retry_until_successful(lambda: self.get_el().click(), **kwargs)

    @property
    def text(self):
        return self.get_el().text

    @property
    def value(self):
        return self.get_el().get_attribute('value')

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

    @property
    def is_checked(self):
        return self.get_el().get_attribute('checked') == 'true'

    def set_checkbox_value(self, is_checked):
        if self.is_checked != is_checked:
            self.get_el().click()

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


class ComponentMetaclass(type):
    def __new__(cls, name, bases, attrs):
        def process_item(item):
            if isinstance(item, PathItem):
                return path_item_to_property(item)
            else:
                return item

        attrs = {k: process_item(v) for k, v in attrs.items()}
        return super(ComponentMetaclass, cls).__new__(cls, name, bases, attrs)


class Component(metaclass=ComponentMetaclass):
    def __init__(self, driver, path=None, el=None):
        self.driver = driver
        self.path = path
        self.el = el

    def __str__(self):
        return "/".join([str(p) for p in self.path])

    def get_element(self, **kwargs): 
        return get_element(self.el, **kwargs) 
 
    def get_elements(self, **kwargs): 
        return get_elements(self.el, **kwargs) 

    def find_elements_by_css_selector(self, css):
        return self.get_elements(css=css)

    def get(self, selector):
        """
        Return an ElementQuery based on the selector. All the following are equivalent: 

        - self.get([Css(".mychild")])
        - self.get(Css(".mychild"))
        - self.get(".mychild")
        """
        if isinstance(selector, str):
            path = [Css(selector)]
        elif not isinstance(selector, Iterable):
            path = [selector]
        return ElementQuery(self.driver, path)

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
