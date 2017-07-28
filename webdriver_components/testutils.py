from threading import Thread
from lxml import etree
from pyquery import PyQuery
import os
from selenium import webdriver


class LocalDriver:
    def __init__(self):
        self.driver = webdriver.Chrome()

    def open_local_file(self, path):
        self.driver.get("file://{}".format(os.path.join(os.getcwd(), path)))

    def cleanup(self):
        try:
            self.driver.close()
        except:
            pass


class DummyDriver:
    def __init__(self, html):
        self.set_html(html)

    def set_html(self, html):
        self.pq = PyQuery(html)

    def get_element(self, **kwargs):
        return self.get_elements(**kwargs)[0]

    def get_elements(self, **kwargs):
        return [DummyElement(e) for e in self.pq(kwargs['css'])]

    def find_elements_by_css_selector(self, css):
        return self.get_elements(css=css)


class DummyElement:
    """
    Wrapper around lxml.etree._Element (returned by PyQuery) to have the same
    interface as a Selenium WebElement.
    """
    def __init__(self, el):
        self.el = el

    def to_string(self):
        return etree.tostring(self.el)

    @property
    def tag_name(self):
        return self.el.tag

    def get_attribute(self, attr_name):
        return self.el.attrib[attr_name]

    def get_element(self, **kwargs):
        return DummyElement(PyQuery(self.el)(kwargs['css'])[0])

    def get_elements(self, **kwargs):
        return [self.get_element(**kwargs)]

    def find_elements_by_css_selector(self, css):
        return self.get_elements(css=css)

    @property
    def text(self):
        return self.el.text





def start_daemon_thread(target):
    t = Thread(target=target)
    t.daemon = True
    t.start()
    return t


