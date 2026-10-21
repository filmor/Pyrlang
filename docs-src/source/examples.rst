Examples!
=========

Talk is cheap! Show me some code!

Have a look in :doc:`cookbook` too!

Some examples are located in the ``examples/`` directory. Run the commands
below from the project root after running ``uv sync``.

For Erlang examples, compile the modules first:

.. code-block:: console

    erlc -o py.erl py.erl/py.erl
    erlc -o examples examples/*.erl

Then start the required module with:

.. code-block:: console

    erl -pa py.erl examples -name erl@127.0.0.1 -setcookie COOKIE -s MODULE -noshell

Replace ``MODULE`` with the example module named below.

1: Python to Erlang
-------------------

Demonstrates how Python node can actively find a running Erlang node and connect
to it by attempting to send a message.

Running (in two terminal tabs):

*   Start Erlang node with ``erl -name erl@127.0.0.1 -setcookie COOKIE``.
*   (optional) Register your shell process as ``shell`` by executing in the
    Erlang shell: ``erlang:register(shell, self()).``
*   ``uv run python examples/e01_simple_node.py`` will start a node at ``py@127.0.0.1`` and using cookie
    ``COOKIE`` will try to connect to Erlang running at ``erl@127.0.0.1``;
*   (optional) Check whether Erlang shell received ``hello`` by typing ``flush().``

2: Erlang to Python
-------------------

Demonstrates how to run a named process on Python node. Erlang node will try and
send message to it by name.

*   ``uv run python examples/e02_registered_process.py`` will register a process as ``my_process`` and you can
    send messages to it by name from Erlang;
*   Start Erlang node with ``erl -name erl@127.0.0.1 -setcookie COOKIE``.
*   In Erlang shell try send something to ``my_process`` like this:
    ``{my_process, 'py@127.0.0.1'} ! {hello, 123, [<<"test">>, self()]}.``
*   In Python terminal tab observe log message about incoming data.

3 & 4: Calling/Batch Python
---------------------------

Examples are ``.erl`` files which demonstrate how remote notebook-style calls
and batch calls will work with Erlang and Python.

*   Run ``uv run python examples/e02_registered_process.py`` to get a running Python node.
*   Start Erlang module ``e03_call_python`` or ``e04_batch_call_python`` and observe what it prints.


5: Links and Monitors of Pyrlang Processes
------------------------------------------

Demonstrates Erlang remotely monitoring and linking to Pyrlang processes.
A Python :py:class:`~pyrlang.process.Process` will trigger monitor and link
messages when exiting.

*   Start Erlang module ``e05_erl_link_monitor_python``.
*   Run ``uv run python examples/e05_erl_link_monitor_python.py`` in another terminal.
*   Pyrlang node will send a message starting the test.
*   Erlang node will spawn a test process, report its pid to Python node.
*   Python node (now knowing the pid) will monitor the Erlang process.
*   Python node will send a exit message to Erlang side, and observe the monitor
    message arriving back.


6 & 7: Links/Monitors of Erlang Processes
-----------------------------------------

Demonstrates Pyrlang remotely linking to and monitoring an Erlang process.

.. note::
    For the monitoring demo, use Erlang module ``e07_py_monitor_erlang`` and
    Python script ``examples/e07_py_monitor_erlang.py`` instead.

*   Start Erlang module ``e06_py_link_erlang``.
*   Run ``uv run python examples/e06_py_link_erlang.py`` in another terminal.
*   Pyrlang node will send a message starting the test.
*   Erlang node will spawn a test process, report its pid to Python node.
*   Python node (now knowing the pid) will monitor the Erlang process.
*   Python node will send a exit message to Erlang side, and observe the monitor
    message arriving back.


10: Elixir and GenServer
------------------------

This example will demonstrate how to accept ``gen_server:call`` in your Python
``Process``.

Running (in two terminal tabs):

*   ``uv run python examples/elixir/e10.py`` will start Python part of Example 10 and start a
    :py:class:`~pyrlang.gen_server.GenServer` example;
*   ``elixir --name elixir@127.0.0.1 --cookie COOKIE examples/elixir/e10.exs``
    will start Elixir part of Example 10 and perform 2
    ``gen_server:call``'s
*   In Elixir terminal tab observe results for 1st and 2nd calls.

.. note::
    Some examples require a client and a server, these have two parts: example A
    and example B.
