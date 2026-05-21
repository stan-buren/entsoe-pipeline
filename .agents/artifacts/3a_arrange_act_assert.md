Title: 3A – Arrange, Act, Assert

URL Source: https://xp123.com/3a-arrange-act-assert/

Published Time: 2011-04-26T12:38:48+00:00

Markdown Content:
Some unit tests are focused, other are like a run-on sentence. How can we create tests that are focused and communicate well? Arrange-act-assert is a pattern for good tests.

> **What’s a good structure for a unit test?**

> **3A: Arrange, Act, Assert**

We want to test the behavior of objects. One good approach is to put an object into each “interesting” configuration it has, and try various actions on it.

Consider the various types of behaviors an object has:

*   Constructors
*   Mutators, also known as modifiers or commands
*   Accessors, also known as queries
*   Iterators

I learned this separation a long time ago but I don’t know the source (though my guess would be some Abstract Data Type research). It’s embodied in Bertrand Meyer’s “command-query separation” principle, and others have independently invented it.

With those distinctions in mind, we can create tests:

**Arrange**: Set up the object to be tested. We may need to surround the object with collaborators. For testing purposes, those collaborators might be test objects (mocks, fakes, etc.) or the real thing.

**Act**: Act on the object (through some mutator). You may need to give it parameters (again, possibly test objects).

**Assert**: Make claims about the object, its collaborators, its parameters, and possibly (rarely!!) global state.

## Where to Begin?

You might think that the Arrange is the natural thing to write first, since it comes first.

When I’m systematically working through an object’s behaviors, I may write the Act line first.

But a useful technique I learned from Jim Newkirk is that writing the Assert first is a great place to start. When you have a new behavior you know you want to test, Assert First lets you start by asking “Suppose it worked; how would I be able to tell?” With the Assert in place, you can do what [Industrial Logic](https://elearning.industriallogic.com/gh/submit?Action=AlbumContentsAction&album=before&devLanguage=Java) calls “Frame First” and lean on the IDE to “fill in the blanks.”

## FAQ

#### _Aren’t some things easier to test with a sequence of actions and assertions?_

Occasionally a sequence is needed, but the 3A pattern is partly a reaction to large tests that look like this:

*   Arrange
*   Act
*   Assert
*   Act
*   Assert
*   Arrange more
*   Act
*   Assert
*   …

To understand a test like that, you have to track state over a series of activities. It’s hard to see what object is the focus of the test, and it’s hard to see that you’ve covered each interesting case. Such multi-step unit tests are usually better off being split into several tests.

But I won’t say “never do it”; there could be some case where the goal is to track a cumulative state and it’s just easier to understand in one series of calls.

#### _Sometimes we want to make sure of our setup. Is it OK to have an extra assert?_

Such a test looks like this:

*   Arrange
*   Assert that the setup is OK
*   Act
*   Assert that the behavior is right

First, consider whether this should be two separate tests, or whether setup is too complicated (if we can’t trust objects to be in the initial state we want). Still, if it seems necessary to do this checking, it’s worth bending the guideline.

#### _What about the notion of having “one assert per test”?_

I don’t follow that guideline too closely. I consider it for two things:

1.   A series of assertions may indicate the object is missing functionality which should be added (and tested). The classical case is equals():It’s better to define an equals() method than (possibly create and) repeat a bunch of assertions about held data.
2.   A series of similar assertions might benefit from a helper (assertion) method.

(If an object has many accessors, it may indicate the object is doing too much.)

When a test modifies an object, I typically find it easiest to consider most accessors together.

For example, consider a list that tracks the number of objects and the maximum entry. One test might look like this:

List list = new List();

 list.add(3);

 assertEquals(1, list.size());

 assertEquals(3, list.max());

That is, it considers the case “what all happens when one item is inserted into an empty list?” Then the various assertions each explore a different “dimension” of the object.

#### _What about setup?_

Most xUnit frameworks let you define a method that is called before each test. This lets you pull out some common code for the tests, and it is part of the initial Arrange. (Thus you have to look in two places to understand the full Arrange-ment.)

#### _What about teardown?_

Most xUnit frameworks let you define a method that is called after each test. For example, if a test opens a file connection, the teardown could close that connection.

If you need teardown, use it, of course. But I’m not adding a fourth A to the pattern: most _unit_ tests don’t need teardown. Unit tests (for the bulk of the system) don’t talk to external systems, databases, files, etc., and Arrange-Act-Assert is a pattern for unit tests.

### History

I (Bill Wake) observed and named the pattern in 2001. “Arrange-Act-Assert” has been the full name the whole time, but it’s been variously abbreviated as AAA or 3A. Kent Beck mentions this pattern in his book [_Test-Driven Development: By Example_](http://www.amazon.com/exec/obidos/ASIN/0321146530/xp123com)(p. 97). This article was written in 2011. Added a description of Assert First and Frame First due to Brian Marick’s comment. [4/26/11]