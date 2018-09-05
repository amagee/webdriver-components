# webdriver-components

webdriver-components is a Python package that helps take away some of the pain
of writing Selenium WebDriver tests. It's based on the Page Object Design
Pattern idea but generalised, so we work by abstracting components of pages,
rather than just pages themselves.

### Why would I use it?

- It works directly with a WebDriver object so it doesn't take away any power
  from you if you need to do some funky Selenium stuff. Use whichever Selenium
  features you like on whichever Selenium-supported browsers you want.
- It helps you avoid repeating yourself; you only need to tell your tests about
  the structure of your HTML components once. This can also reduce the amount of
  time you spend updating your tests to accommodate changes in your HTML
  structure.
- It's designed to be robust against race conditions. For example if you tell it
  to click a button, but the button isn't ready yet, it will retry until clicking
  the button is possible or there is a timeout.

## How would I use it?


#### Getting started is very straightforward.


    $ pip install webdriver-components


#### Imports and setup:


    from selenium import webdriver
    from webdriver_components.pageobjects import Component, Css
    import urllib

    # For these demos we're so lazy we're not even bothering to create any files on disk;
    # we're going to serve our content directly from strings using data: urls.
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URIs
    def open_page(driver, html):
        driver.get("data:text/html," + urllib.parse.quote(html))
    
    # Or whichever browser you like
    driver = webdriver.Chrome()


#### Single elements

Now let's create our first Component. Suppose we have a page that's just a
couple of text fields for a person's first and last names. We can identify the
fields by their CSS classes like so:


    class NameForm(Component):
        first_name = Css('.first-name')
        last_name = Css('.last-name')

- Note that `Css` is currently the only supported way to describe selectors.

Then we can instantiate the NameForm using a WebDriver object and use it to
interact with the page:

    open_page(driver, """
        First name <input class="first-name"> <br />
        Last name <input class="last-name">
    """)

    # Connect a NameForm to the WebDriver. This doesn't interact with the page yet.
    form = NameForm(driver)

    # Now we can type into the text boxes:
    form.first_name.set_text('Andrew')
    form.last_name.set_text('Magee')

    # And assert that we did it right:
    assert form.first_name.value == 'Andrew'
    assert form.last_name.value == 'Magee'

#### Multiple elements

But we don't have to have just one name on a page. Let's make our top-level
element instead be a component that has two NameForms:

    class MultipleNameForms(Component):
        # Note that the `factory` parameter is a callable that returns the
        # `Component`-subclass we want. This is so we can define the sub-components
        # after the super-components, to structure our source file in a natural way.
        name_form_1 = Css('.name-form-1', factory=lambda: NameForm)
        name_form_2 = Css('.name-form-2', factory=lambda: NameForm)

Using this is just as straightforward:

    open_page(driver, """
        <div class="name-form-1">
            <h3>Name form 1</h3>
            First name <input class="first-name"> <br />
            Last name <input class="last-name">
        </div>
        <div class="name-form-2">
            <h3>Name form 2</h3>
            First name <input class="first-name"> <br />
            Last name <input class="last-name">
        </div>
    """)

    forms = MultipleNameForms(driver)
    forms.name_form_1.set_name('Andrew', 'Magee')
    forms.name_form_2.set_name('Sally', 'Smith')

    assert forms.name_form_1.first_name.value == 'Andrew'
    assert forms.name_form_2.first_name.value == 'Sally'

#### Repeated elements

We can handle repeated elements (eg. lists) by passing `multiple=True`:


    class ListPage(Component):
        list_items = Css(".mylist li", multiple=True)

    open_page(driver, """
      <ul class="mylist">
        <li>first item</li>
        <li>second item</li>
        <li>third item</li>
      </ul>
    """)

    list_page = ListPage(driver)
    # list_page.list_items is list-like, we can index it:
    assert list_page.list_items[1].text == 'second item'
    # and iterate through it:
    assert [l.text for l in list_page.list_items] == [
        'first item',
        'second item',
        'third item'
    ]

We can even combine multiple=True and factory:

    class FactoryListPage(Component):
        list_items = Css(".mylist li", multiple=True, factory=lambda: MyListItem)

    class MyListItem(Component):
        name = Css(".name")
        email = Css(".email")

    open_page(driver, """
      <ul class="mylist">
        <li>
            <span class="name">Andrew Magee</span>
            <span class="email">amagee@example.com</span>
        </li>
        <li>
            <span class="name">Sally Smith</span>
            <span class="email">sally@example.com</span>
        </li>
      </ul>
    """)

    factory_list_page = FactoryListPage(driver)
    assert factory_list_page.list_items[1].email.text == "sally@example.com"

### Auto-retrying

Here's an example demonstrating that `webdriver_elements` will automatically
retry if you tell it to click an element that isn't clickable. In this case we
have a page with a button that is only displayed after waiting for one second,
but everything is still fine.

    class DelayedButtonPage(Component):
        button = Css('#mybutton')
        output = Css('#output')

    open_page(driver, """
      <button id="mybutton" style="display: none;">Click me</button>
      <span id="output"></span>
      <script>
        window.onload = function() {
          var button = document.getElementById('mybutton');
          button.addEventListener('click', function() {
            document.getElementById('output').innerHTML = 'clicked!';
          });
          setTimeout(function() {
            document.getElementById('mybutton').style.display = 'inline';
          }, 1000);
        };
      </script>
    """)

    delayed_button_page = DelayedButtonPage(driver)
    delayed_button_page.button.click()
    assert delayed_button_page.output.text == "clicked!"
