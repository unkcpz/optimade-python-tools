"""This submodule implements some useful utilities for dealing
with OPTIMADE providers that can be used in server or client code.

"""

from typing import List, Union, Optional, Dict, Any
from pathlib import Path

try:
    import simplejson as json
except ImportError:
    import json

from pydantic import AnyHttpUrl

from optimade.models.links import LinksResource
from optimade.models.responses import LinksResponse

PROVIDER_LIST_URLS = (
    "https://providers.optimade.org/v1/links",
    "https://raw.githubusercontent.com/Materials-Consortia/providers/master/src/links/v1/providers.json",
)


def mongo_id_for_database(database_id: str, database_type: str) -> str:
    """Produce a MongoDB ObjectId for a database"""
    from bson.objectid import ObjectId

    oid = f"{database_id}{database_type}"
    if len(oid) > 12:
        oid = oid[:12]
    elif len(oid) < 12:
        oid = f"{oid}{'0' * (12 - len(oid))}"

    return str(ObjectId(oid.encode("UTF-8")))


def get_providers(
    add_mongo_id: bool = False, source: Optional[Union[AnyHttpUrl, Path]] = None
) -> list:
    """Retrieve Materials-Consortia providers (from https://providers.optimade.org/v1/links),
    unless an alternative source is requested.

    Fallback order if providers.optimade.org is not available:

    1. Try Materials-Consortia/providers on GitHub.
    2. Try submodule `providers`' list of providers.
    3. Log warning that providers list from Materials-Consortia is not included in the
       `/links`-endpoint.

    Arguments:
        add_mongo_id: Whether to populate the `_id` field of the provider with a MongoDB ObjectID.
        source: A custom source to query, either an HTTP URL or a file path.

    Returns:
        List of raw JSON-decoded providers including MongoDB object IDs.

    """
    import requests

    remote_providers = list(PROVIDER_LIST_URLS)

    if source is not None:
        if isinstance(source, Path):
            with open(source, "r") as f:
                providers = LinksResponse(**json.load(f))

        else:
            remote_providers = [source]
            # Try to add some other URLs so that source can be just e.g., `https://providers.optimade.org`
            if not source.endswith("/v1/links") or not source.endswith("/links"):
                remote_providers.extend([f"{source}/v1/links", f"{source}/links"])

    for provider_list_url in remote_providers:
        try:
            providers = LinksResponse(**requests.get(provider_list_url).json())
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ConnectTimeout,
            json.JSONDecodeError,
        ):
            pass
        else:
            break

    if not providers:
        if source is not None:
            raise RuntimeError(f"Unable to retrieve providers list from {source}.")
        try:
            # Fallback to pulling from the providers submodule
            from optimade.server.data import providers as submodule_providers

            providers = LinksResponse(**submodule_providers)
        except ImportError as exc:
            raise RuntimeError(
                "Unable to retrieve providers list.\nTried remote resources: {remote_providers}\nand the providers submodule."
            ) from exc

    return _unpack_providers(providers, add_mongo_id=add_mongo_id)


def _unpack_providers(
    providers: LinksResponse, add_mongo_id: bool
) -> List[Dict[str, Any]]:
    """Convert a provider links response to a list of providers with
    attributes 'popped' to the top-level of the dictionary.

    Parameters:
        providers: The LinksResponse from the provider list.
        add_mongo_id: Whether to add MongoDB object IDs to the providers.

    """

    providers_list = []
    for provider in providers.data:
        if isinstance(provider, LinksResource):
            _provider = json.loads(provider.json())
        else:
            _provider = provider
        # Remove/skip "exmpl"
        if _provider["id"] == "exmpl":
            continue

        _provider.update(_provider.pop("attributes", {}))

        # Add MongoDB ObjectId
        if add_mongo_id:
            _provider["_id"] = {
                "$oid": mongo_id_for_database(_provider["id"], _provider["type"])
            }

        providers_list.append(_provider)

    return providers_list


def get_child_database_links(
    provider: Union[LinksResource, Dict[str, Any]]
) -> List[LinksResource]:
    """For a provider, retrieve a list of available child databases.

    Arguments:
        provider: The links entry for the provider.

    Returns:
        A list of the valid links entries from this provider that
        have `link_type` `"child"`.

    """
    import requests
    from optimade.models.responses import LinksResponse
    from optimade.models.links import LinkType

    if isinstance(provider, LinksResource):
        _id = provider.id
        base_url = str(provider.attributes.base_url)
    else:
        _id = provider.pop("id")
        base_url = provider.pop("base_url")

    if base_url is None:
        raise RuntimeError(f"Provider {_id} provides no base URL.")

    links_endp = base_url + "/v1/links"
    links = requests.get(links_endp)

    if links.status_code != 200:
        raise RuntimeError(
            f"Invalid response from {links_endp} for provider {_id}: {links.content!r}."
        )

    _links = LinksResponse(**links.json())

    # Unpack links that are stored as `LinksResource` objects, or as raw dictionaries
    try:
        return [
            link
            for link in _links.data
            if link.attributes.link_type == LinkType.CHILD
            and link.attributes.base_url is not None
        ]
    except AttributeError:
        return [
            link
            for link in _links.data
            if link.get("attributes", {}).get("link_type", None) == "child"
            and link.get("attributes", {}).get("base_url") is not None
        ]
