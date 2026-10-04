import os
import typing

import bs4

import edq.clilib.model
import edq.util.dirent

CSS_CLASS_MODULE_DOCS: str = 'edq-cli-module-docs'
CSS_CLASS_PACKAGE_DOCS: str = 'edq-cli-package-docs'
CSS_CLASS_PACKAGE_DIRENT: str = 'edq-cli-package-dirent'

def update_pdoc(package_dir: str, base_qualified_name: str, docs_base_dir: str) -> None:
    """
    Update a built pdoc HTML documentation dir with information about CLI utils from the given package dir.
    This will add information (like usage) to the HTML documentation.

    The base docs dir should be such that we can use a module's qualified name to locate the documentation file,
    e.g., `edq.cli.version` -> `<base docs dir>/edq/cli/version.html`.
    """

    package = edq.clilib.model.CLIPackage.from_path(package_dir, base_qualified_name)
    if (package is None):
        raise ValueError(f"Target dir is not a CLI package: '{package_dir}'.")

    _update_package(package, docs_base_dir)

def _update_package(package: edq.clilib.model.CLIPackage, docs_base_dir: str) -> None:
    """ Recursively update the documentation for a package. """

    _update_package_docs(package, docs_base_dir)

    for entry in package.dirents:
        if (isinstance(entry, edq.clilib.model.CLIModule)):
            _update_module_docs(entry, docs_base_dir)
        elif (isinstance(entry, edq.clilib.model.CLIPackage)):
            _update_package(entry, docs_base_dir)
        else:
            raise ValueError(f"Unknown CLI type: '{type(entry)}'.")

def _update_package_docs(package: edq.clilib.model.CLIPackage, docs_base_dir: str) -> None:
    """ Update the documentation for a package. """

    path = _get_docs_path(package, docs_base_dir)

    # The base rel name needs to point to the parent.
    base_rel_name = '.'.join(package.qualified_name.split('.')[0:-1])

    lines: typing.List[str] = []
    _list_package(package, docs_base_dir, base_rel_name, lines)

    if (len(lines) == 0):
        return

    content = '<p>This package contains the following CLI tools:</p><hr />'
    content += "\n<hr />\n".join(lines)

    _insert_html(path, CSS_CLASS_PACKAGE_DOCS, content)

def _list_package(
        package: edq.clilib.model.CLIPackage,
        docs_base_dir: str,
        base_rel_name: str,
        lines: typing.List[str],
        ) -> None:
    """ List the contents of a package for a docs page. """

    for entry in package.dirents:
        rel_name = entry.qualified_name.removeprefix(base_rel_name + '.')

        parts = rel_name.split('.')
        parts[-1] += '.html'
        rel_href = '/'.join(parts)

        if (isinstance(entry, edq.clilib.model.CLIModule)):
            html = f"""
                <div class='{CSS_CLASS_PACKAGE_DIRENT}'>
                    <a href='{rel_href}'>{entry.qualified_name}</a>
                    <p>
                        {entry.get_description()}
                    </p><pre><code>{entry.get_usage_text()}</code></pre>
                </div>
            """
            lines.append(html)
        elif (isinstance(entry, edq.clilib.model.CLIPackage)):
            html = f"""
                <div class='{CSS_CLASS_PACKAGE_DIRENT}'>
                    <a href='{rel_href}'>{entry.qualified_name}.*</a>
                    <p>
                        {entry.get_description()}
                    </p>
                </div>
            """
            lines.append(html)

            _list_package(entry, docs_base_dir, base_rel_name, lines)
        else:
            raise ValueError(f"Unknown CLI type: '{type(entry)}'.")

def _update_module_docs(module: edq.clilib.model.CLIModule, docs_base_dir: str) -> None:
    """ Update the documentation for a module. """

    path = _get_docs_path(module, docs_base_dir)
    content = f"<div class='.{CSS_CLASS_MODULE_DOCS}'><pre><code>{module.get_help_text()}</code></pre></div>"
    _insert_html(path, CSS_CLASS_MODULE_DOCS, content)

def _insert_html(path: str, css_class: str, content: str) -> None:
    """ Insert HTML into a doc file. """

    text = edq.util.dirent.read_file(path)
    document = bs4.BeautifulSoup(text, 'html.parser')

    # Check for previous content.
    tags = document.select(f"div.{css_class}")
    for tag in tags:
        tag.decompose()

    # Add in new content.
    parents = document.select('.module-info .docstring')
    if (len(parents) != 1):
        raise ValueError(f"Could not find exactly one HTML docstring (found {len(parents)}): '{path}'.")

    new_tag = bs4.BeautifulSoup(content, 'html.parser')

    parents[0].append(new_tag)

    edq.util.dirent.write_file(path, str(document))

def _get_docs_path(dirent: edq.clilib.model.CLIDirent, docs_base_dir: str) -> str:
    """ Create the relative path for a CLI dirent's HTML documentation from its qualified name. """

    parts = dirent.qualified_name.split('.')
    parts[-1] += '.html'
    return os.path.join(docs_base_dir, *parts)
