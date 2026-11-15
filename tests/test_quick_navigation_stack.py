"""QuickNavigationStack: push the view you leave, pop it to go back."""
from rat.ui.quick_navigation_stack import QuickNavigationStack


def test_pop_returns_the_view_pushed_last():
    stack = QuickNavigationStack()
    stack.push("answer")
    stack.push("page")
    assert stack.pop() == "page"
    assert stack.pop() == "answer"
    assert stack.pop() is None


def test_pop_on_empty_stack_is_none():
    assert QuickNavigationStack().pop() is None
