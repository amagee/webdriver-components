# webdriver-components

webdriver-components is a Python package that takes away some of the pain
of writing Selenium tests. It's an extension of the [page object
design pattern](https://martinfowler.com/bliki/PageObject.html) where we think in 
terms of components rather than just pages.

### Why?

Components are super useful in helping make composable, well-factored
frontends.  Suppose you're making a todo app - you might have `TodoList`
components in various places, and `TodoList` components might contain `Todo`
components. In all the popular frontend frameworks (React, Vue, Angular...)
you can express this directly. In React this might look like:

```javascript
let todos = {/* some list of todos */};

function Page() {
  return <TodoList />;
}

function TodoList() {
  return <div className="todo-list">
    {todos.map((todo) => (
      <Todo todo={todo} key={todo.id} />
    ))}
  </div>;
}

function Todo() {
  return <div className="todo">
    <span className="name">
      {todo.name}
    </span>
    <input type="checkbox" />
  </div>
}
```

Why not also express it directly in your tests?

In webdriver-components you could write:

```python
class Page(Component):
    todo_list = Css(".todo-list", factory=TodoList)

class TodoList(Component):
    todos = Css(".todo", factory=Todo, multiple=True)

class Todo(Component):
    name = Css(".name")
    checkbox = Css("input[type=checkbox]")
    # … list whatever elements in the Todo we might want to test

    def toggle_done(self):
        self.checkbox.click()
```

And then you can test your todos:

```python
def test_my_todos():
    driver = <your WebDriver object>
    page = Page(driver)
    assert len(page.todo_list) == 3
    assert page.todo_list.todos[0].name.text == "My first todo"
```

Now we have a single, obvious place which is the only place our tests will
need to know about the internal structure of a `Todo`. We can also use it
whereever todo lists might appear. If we decide to have two todo lists, we can
just update the page:

```python
class Page(Component):
    fun_todo_list = Css(".fun-todo-list", factory=TodoList)
    boring_todo_list = Css(".boring-todo-list", factory=TodoList)
```

Or we can have todo lists on separate pages:

```python
class FunPage(Component):
    todo_list = Css(".todo-list", factory=TodoList)

class BoringPage(Component):
    todo_list = Css(".todo-list", factory=TodoList)
```

#### classnames?

The examples above use CSS class names to identify the elements we're talking
about. You don't have to use class names! You might prefer to use [data
attributes](https://developer.mozilla.org/en-US/docs/Learn/HTML/Howto/Use_data_attributes) .

The example above would work if we instead did:

```javascript
function TodoList() {
  return <div data-t="todo-list">
    ...
  </div>;
}
```

```python
class Page(Component):
    todo_list = Css("[data-t=todo-list]")
```

webdriver-components does not know anything about React or Vue or Angular, though, so
you will need to use selectors to identify your elements using just the rendered DOM structure.


#### Other perks:

- It works directly with a WebDriver object so it doesn't take away any power
  from you if you need to do some funky Selenium stuff. Use whichever Selenium
  features you like on whichever Selenium-supported browsers you want.
- It's designed to be robust against race conditions. For example if you tell it
  to click a button, but the button isn't ready yet, it will retry until clicking
  the button is possible or there is a timeout.

## How would I use it?


#### Getting started is very straightforward.


    $ pip install webdriver-components


#### Imports and setup:


```python
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
```


#### Single elements

Now let's create our first Component. Suppose we have a page that's just a
couple of text fields for a person's first and last names. We can identify the
fields by their CSS classes like so:


```python
class NameForm(Component):
    first_name = Css('.first-name')
    last_name = Css('.last-name')
```

- Note that `Css` is currently the only supported way to describe selectors.

Then we can instantiate the NameForm using a WebDriver object and use it to
interact with the page:

```python
open_page(driver, """
    First name <input class="first-name"> <br />
    Last name <input class="last-name">
""")

# Connect a NameForm to the WebDriver. This doesn't interact with the page yet.
form = NameForm(driver)

# Now we can type into the text boxes:
form.first_name.set_text('Andrew')
form.last_name.set_text('Magee')

# Note that the above is equivalent to:
# form.get(".first-name").set_text("Andrew") # etc
# or
# form.get(Css(".first-name")).set_text("Andrew") # etc
# or
# form.get([Css(".first-name")]).set_text("Andrew") # etc

# And assert that we did it right:
assert form.first_name.value == 'Andrew'
assert form.last_name.value == 'Magee'
```

#### Multiple elements

But we don't have to have just one name on a page. Let's make our top-level
element instead be a component that has two NameForms:

```python
class MultipleNameForms(Component):
    # Note that the `factory` parameter is a callable that returns the
    # `Component`-subclass we want. This is so we can define the sub-components
    # after the super-components, to structure our source file in a natural way.
    name_form_1 = Css('.name-form-1', factory=lambda: NameForm)
    name_form_2 = Css('.name-form-2', factory=lambda: NameForm)
```

Using this is just as straightforward:

```python
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
```

#### Repeated elements

We can handle repeated elements (eg. lists) by passing `multiple=True`:


```python
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
```

We can even combine multiple=True and factory:

```python
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
```

### Auto-retrying

Here's an example demonstrating that `webdriver_elements` will automatically
retry if you tell it to click an element that isn't clickable. In this case we
have a page with a button that is only displayed after waiting for one second,
but everything is still fine.

```python
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
```
