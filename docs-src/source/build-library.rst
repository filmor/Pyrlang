Building the Library
====================

If you just want to get going just install pyralng using :code:`pip` the dependancy
:code:`pyrlang-term` will be installed automatically

.. code-block:: console

  pip3 install pyrlang


To install Pyrlang from source, check out the project and use :code:`uv`.
The :code:`pyrlang-term` dependency is installed automatically from
https://github.com/Pyrlang/Term.git:

.. code-block:: console

  git clone git@github.com:Pyrlang/Pyrlang.git
  cd Pyrlang
  uv sync --no-dev



To build the docs, install the development dependency group, which includes
Sphinx and the other documentation tools:

.. code-block:: console

  uv sync

Source for the documentation is in the ``docs-src/`` directory. To generate
HTML from the project root, run:

.. code-block:: console

  uv run sphinx-build -b html docs-src/source docs
