import pytest
from time import sleep
from webdriver_components.pageobjects import Component, Css
from webdriver_components.testutils import start_daemon_thread, LocalDriver, DummyDriver
from webdriver_components.utils import retry_until_true, monkeypatch_webdriver_objects
from webdriver_components.tablerow import TableRow


class LoginPage(Component):
    login_form = Css('#login-form', factory=lambda: LoginForm)
    list_items = Css(
        '.list-item',
        multiple=True,
        query_methods={
            'get_item_by_text': 
                lambda self, text: [el for el in self if el.text.strip() == text][0]
        }
    )
    increment_counter_button = Css('#increment-counter-button')
    counter = Css('#counter')

    text_input = Css("#text-input")
    checkbox = Css("#checkbox")

    table_rows = Css("#table tr", multiple=True, factory=lambda: MyTableRow)

    nonexistent_item = Css("#this-does-not-exist")


class MyTableRow(TableRow):
    cell_names = ('column1', 'column2', 'column3')


class LoginForm(Component):
    email_input = Css('.login-widget__email-input')
    password_input = Css('.login-widget__password-input')

    def login(self, email, password):
        self.email_input.set_text(email)
        self.password_input.set_text(password)


def test_elements_work_without_contacting_driver():
    l = LoginForm(driver=None)
    assert l.email_input.path == [Css('.login-widget__email-input')]
    assert l.password_input.path == [Css('.login-widget__password-input')]


def test_nested_elements():
    l = LoginPage(driver=DummyDriver("""
        <div id="login-form">
            <input class="login-widget__email-input" />
        </div>
    """))
    el = l.login_form.email_input
    assert str(el) == "LoginForm(css=#login-form)/[css=.login-widget__email-input]"
    assert el.path == [Css('#login-form'), Css('.login-widget__email-input')] 
    assert el.get_el().get_attribute("class") == "login-widget__email-input"


def test_multiple_elements():
    l = LoginPage(driver=DummyDriver("""
        <div id="login-form">
            <div class="list-item">
                item 1
            </div>
            <div class="list-item">
                item 2
            </div>
            <div class="list-item">
                item 3
            </div>
        </div>
    """))
    els = l.list_items.get_el()
    assert [el.text.strip() for el in els] == ['item 1', 'item 2', 'item 3']


def test_exists_false():
    l = LoginPage(driver=DummyDriver("""
        <div id="login-form">
            There's nothing here
        </div>
    """))

    assert l.nonexistent_item.exists() is False


@pytest.mark.parametrize('driver_type', ['dummy', 'real'])
def test_multiple_elements_index(driver_type):
    try:
        if driver_type == 'dummy':
            ld = None
            driver = DummyDriver("""
                <div id="login-form">
                    <div class="list-item">
                        item 1
                    </div>
                    <div class="list-item">
                        item 2
                    </div>
                    <div class="list-item">
                        item 3
                    </div>
                </div>
            """)
        else:
            ld = LocalDriver()
            ld.open_local_file("test1.html")
            driver = ld.driver

        l = LoginPage(driver=driver)
        assert l.list_items[0].get_el().text.strip() == "item 1"
        assert l.list_items[1].get_el().text.strip() == "item 2"
    finally:
        if ld is not None:
            ld.cleanup()



def test_iterate_over_multiple_elements(local_driver):
    local_driver.open_local_file("test1.html")
    l = LoginPage(local_driver.driver)
    assert [l.text for l in l.list_items] == ['item 1', 'item 2', 'item 3']


def test_custom_query_method():
    l = LoginPage(driver=DummyDriver("""
        <div id="login-form">
            <div class="list-item">
                item 1
            </div>
            <div class="list-item">
                item 2
            </div>
            <div class="list-item">
                item 3
            </div>
        </div>
    """))

    assert l.list_items.get_item_by_text(text="item 2").path[-1].name == 'get_item_by_text'
    assert l.list_items.get_item_by_text(text="item 2").path[-1].kwargs == {'text': 'item 2'}
    assert(l.list_items.get_item_by_text(text="item 2").get_el().text.strip() == "item 2")



def test_waiting_for_el():
    """
    Call .get_el() while an element does not exist, then make it appear, and
    assert that the call returns the correct element anyway.
    """
    driver = DummyDriver("""
        <div id="login-form">
            Loading...
        </div>
    """)

    l = LoginPage(driver=driver)
    email_input = None

    def get_element():
        nonlocal email_input
        email_input = l.login_form.email_input.get_el()

    def load_page():
        driver.set_html("""
            <div id="login-form">
                <input class="login-widget__email-input" />
            </div>
        """)

    t1 = start_daemon_thread(target=get_element)
    sleep(1)
    t2 = start_daemon_thread(target=load_page)

    t1.join()
    assert email_input is not None


def test_selenium(local_driver):
    local_driver.open_local_file("test1.html")
    l = LoginPage(local_driver.driver)
    assert l.list_items[0].get_el().text.strip() == "item 1"


def test_click_element(local_driver):
    local_driver.open_local_file("test1.html")
    l = LoginPage(local_driver.driver)
    l.increment_counter_button.click()
    retry_until_true(lambda: l.counter.text.strip() == '1')


def test_set_text(local_driver):
    local_driver.open_local_file("test1.html")
    l = LoginPage(local_driver.driver)
    l.text_input.set_text("new text")
    assert l.text_input.value == "new text"


def test_method_on_factory_element(local_driver):
    local_driver.open_local_file("test1.html")
    l = LoginPage(local_driver.driver)
    l.login_form.login('amagee@example.com', 'password')
    assert l.login_form.email_input.value == "amagee@example.com"
    assert l.login_form.password_input.value == "password"


def test_set_checkbox_value(local_driver):
    local_driver.open_local_file("test1.html")
    l = LoginPage(local_driver.driver)
    c = l.checkbox
    assert c.is_checked
    l.checkbox.set_checkbox_value(False)
    assert not c.is_checked


def test_tablerow(local_driver):
    local_driver.open_local_file("test1.html")
    l = LoginPage(local_driver.driver)
    assert str(l.table_rows) == "MyTableRow(css=#table tr)*"
    assert not hasattr(l.table_rows, 'column1_cell')
    assert str(l.table_rows[0]) == "MyTableRow(css=#table tr)*/MyTableRow(index=0)"
    assert str(l.table_rows[0].column1_cell)  == "MyTableRow(css=#table tr)*/MyTableRow(index=0)/[css=td:nth-child(1)]"
    assert l.table_rows[0].column1_cell.text.strip() == "Row 1 cell 1"
    assert l.table_rows[0].column1 == "Row 1 cell 1"
    assert l.table_rows[0].data == {
        'column1': "Row 1 cell 1",
        'column2': "Row 1 cell 2",
        'column3': "Row 1 cell 3",
    }


def test_monkeypatch_webdriver(local_driver):
    local_driver.open_local_file("test1.html")
    monkeypatch_webdriver_objects()
    assert local_driver.driver.get_element("#table").tag_name == "table"


