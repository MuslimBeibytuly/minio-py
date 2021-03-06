# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage, (C)
# 2020 MinIO, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Response of ListBuckets, ListObjects, ListObjectsV2 and ListObjectVersions API.
"""

from __future__ import absolute_import

from urllib.parse import unquote
from xml.etree import ElementTree as ET

from .helpers import strptime_rfc3339
from .xml import find, findall, findtext


class Bucket:
    """Bucket information."""

    def __init__(self, name, creation_date):
        self._name = name
        self._creation_date = creation_date

    @property
    def name(self):
        """Get name."""
        return self._name

    @property
    def creation_date(self):
        """Get creation date."""
        return self._creation_date


class ListAllMyBucketsResult:
    """LissBuckets API result."""

    def __init__(self, buckets):
        self._buckets = buckets

    @property
    def buckets(self):
        """Get buckets."""
        return self._buckets

    @classmethod
    def fromxml(cls, element):
        """Create new object with values from XML element."""
        element = find(element, "Buckets")
        buckets = []
        if element is not None:
            elements = findall(element, "Bucket")
            for bucket in elements:
                name = findtext(bucket, "Name", True)
                creation_date = findtext(bucket, "CreationDate")
                if creation_date:
                    creation_date = strptime_rfc3339(creation_date)
                buckets.append(Bucket(name, creation_date))
        return cls(buckets)


class Object:
    """Object information."""

    def __init__(self,  # pylint: disable=too-many-arguments
                 bucket_name,
                 object_name,
                 last_modified=None, etag=None,
                 size=None, metadata=None,
                 version_id=None, is_latest=None, storage_class=None,
                 owner_id=None, owner_name=None, content_type=None):
        self._bucket_name = bucket_name
        self._object_name = object_name
        self._last_modified = last_modified
        self._etag = etag
        self._size = size
        self._metadata = metadata
        self._version_id = version_id
        self._is_latest = is_latest
        self._storage_class = storage_class
        self._owner_id = owner_id
        self._owner_name = owner_name
        self._content_type = content_type

    @property
    def bucket_name(self):
        """Get bucket name."""
        return self._bucket_name

    @property
    def object_name(self):
        """Get object name."""
        return self._object_name

    @property
    def is_dir(self):
        """Get whether this key is a directory."""
        return self._object_name.endswith("/")

    @property
    def last_modified(self):
        """Get last modified time."""
        return self._last_modified

    @property
    def etag(self):
        """Get etag."""
        return self._etag

    @property
    def size(self):
        """Get size."""
        return self._size

    @property
    def metadata(self):
        """Get metadata."""
        return self._metadata

    @property
    def version_id(self):
        """Get version ID."""
        return self._version_id

    @property
    def is_latest(self):
        """Get is-latest flag."""
        return self._is_latest

    @property
    def storage_class(self):
        """Get storage class."""
        return self._storage_class

    @property
    def owner_id(self):
        """Get owner ID."""
        return self._owner_id

    @property
    def owner_name(self):
        """Get owner name."""
        return self._owner_name

    @property
    def is_delete_marker(self):
        """Get whether this key is a delete marker."""
        return self._size is None and self._version_id is not None

    @property
    def content_type(self):
        """Get content type."""
        return self._content_type

    @classmethod
    def fromxml(cls, element, bucket_name):
        """Create new object with values from XML element."""
        tag = findtext(element, "LastModified")
        last_modified = None if tag is None else strptime_rfc3339(tag)

        tag = findtext(element, "ETag")
        etag = None if tag is None else tag.replace('"', "")

        tag = findtext(element, "Size")
        size = None if tag is None else int(tag)

        tag = find(element, "Owner")
        owner_id, owner_name = (
            (None, None) if tag is None
            else (findtext(tag, "ID"), findtext(tag, "DisplayName"))
        )

        tag = find(element, "UserMetadata") or []
        metadata = {}
        for child in tag:
            key = child.tag.split("}")[1] if "}" in child.tag else child.tag
            metadata[key] = child.text

        return cls(
            bucket_name,
            findtext(element, "Key"),
            last_modified=last_modified,
            etag=etag,
            size=size,
            version_id=findtext(element, "VersionId"),
            is_latest=findtext(element, "IsLatest"),
            storage_class=findtext(element, "StorageClass"),
            owner_id=owner_id,
            owner_name=owner_name,
            metadata=metadata,
        )


def parse_list_objects(response, bucket_name):
    """Parse ListObjects/ListObjectsV2/ListObjectVersions response."""
    element = ET.fromstring(response.data.decode())
    elements = findall(element, "Contents")
    objects = [Object.fromxml(tag, bucket_name) for tag in elements]
    marker = objects[-1].object_name if objects else None

    elements = findall(element, "Version")
    objects += [Object.fromxml(tag, bucket_name) for tag in elements]

    elements = findall(element, "CommonPrefixes")
    objects += [
        Object(bucket_name, findtext(tag, "Prefix"))
        for tag in elements
    ]

    elements = findall(element, "DeleteMarker")
    objects += [Object.fromxml(tag, bucket_name) for tag in elements]

    is_truncated = (findtext(element, "IsTruncated") or "").lower() == "true"
    key_marker = findtext(element, "NextKeyMarker")
    version_id_marker = findtext(element, "NextVersionIdMarker")
    continuation_token = findtext(element, "NextContinuationToken")
    if key_marker is not None:
        continuation_token = key_marker
    if continuation_token is None:
        continuation_token = findtext(element, "NextMarker")
    if continuation_token is None and is_truncated:
        continuation_token = marker
    return objects, is_truncated, continuation_token, version_id_marker


class CompleteMultipartUploadResult:
    """CompleteMultipartUpload API result."""

    def __init__(self, response):
        element = ET.fromstring(response.data.decode())
        self._bucket_name = findtext(element, "Bucket")
        self._object_name = findtext(element, "Key")
        self._location = findtext(element, "Location")
        self._etag = findtext(element, "ETag")
        if self._etag:
            self._etag = self._etag.replace('"', "")
        self._version_id = response.getheader("x-amz-version-id")
        self._http_headers = response.getheaders()

    @property
    def bucket_name(self):
        """Get bucket name."""
        return self._bucket_name

    @property
    def object_name(self):
        """Get object name."""
        return self._object_name

    @property
    def location(self):
        """Get location."""
        return self._location

    @property
    def etag(self):
        """Get etag."""
        return self._etag

    @property
    def version_id(self):
        """Get version ID."""
        return self._version_id

    @property
    def http_headers(self):
        """Get HTTP headers."""
        return self._http_headers


class Part:
    """Part information of a multipart upload."""

    def __init__(self, part_number, etag, last_modified=None, size=None):
        self._part_number = part_number
        self._etag = etag
        self._last_modified = last_modified
        self._size = size

    @property
    def part_number(self):
        """Get part number. """
        return self._part_number

    @property
    def etag(self):
        """Get etag."""
        return self._etag

    @property
    def last_modified(self):
        """Get last-modified."""
        return self._last_modified

    @property
    def size(self):
        """Get size."""
        return self._size

    @classmethod
    def fromxml(cls, element):
        """Create new object with values from XML element."""
        part_number = findtext(element, "PartNumber", True)
        etag = findtext(element, "ETag", True)
        etag = etag.replace('"', "")
        tag = findtext(element, "LastModified")
        last_modified = None if tag is None else strptime_rfc3339(tag)
        size = findtext(element, "Size")
        if size:
            size = int(size)
        return cls(part_number, etag, last_modified, size)


class ListPartsResult:
    """ListParts API result."""

    def __init__(self, response):
        element = ET.fromstring(response.data.decode())
        self._bucket_name = findtext(element, "Bucket")
        self._object_name = findtext(element, "Key")
        tag = find(element, "Initiator")
        self._initiator_id = (
            None if tag is None else findtext(tag, "ID")
        )
        self._initiator_name = (
            None if tag is None else findtext(tag, "DisplayName")
        )
        tag = find(element, "Owner")
        self._owner_id = (
            None if tag is None else findtext(tag, "ID")
        )
        self._owner_name = (
            None if tag is None else findtext(tag, "DisplayName")
        )
        self._storage_class = findtext(element, "StorageClass")
        self._part_number_marker = findtext(element, "PartNumberMarker")
        self._next_part_number_marker = findtext(
            element, "NextPartNumberMarker",
        )
        if self._next_part_number_marker:
            self._next_part_number_marker = int(self._next_part_number_marker)
        self._max_parts = findtext(element, "MaxParts")
        if self._max_parts:
            self._max_parts = int(self._max_parts)
        self._is_truncated = findtext(element, "IsTruncated")
        self._is_truncated = (
            self._is_truncated is not None and
            self._is_truncated.lower() == "true"
        )
        self._parts = [Part.fromxml(tag) for tag in findall(element, "Part")]

    @property
    def bucket_name(self):
        """Get bucket name."""
        return self._bucket_name

    @property
    def object_name(self):
        """Get object name."""
        return self._object_name

    @property
    def initiator_id(self):
        """Get initiator ID."""
        return self._initiator_id

    @property
    def initator_name(self):
        """Get initiator name."""
        return self._initiator_name

    @property
    def owner_id(self):
        """Get owner ID."""
        return self._owner_id

    @property
    def owner_name(self):
        """Get owner name."""
        return self._owner_name

    @property
    def storage_class(self):
        """Get storage class."""
        return self._storage_class

    @property
    def part_number_marker(self):
        """Get part number marker."""
        return self._part_number_marker

    @property
    def next_part_number_marker(self):
        """Get next part number marker."""
        return self._next_part_number_marker

    @property
    def max_parts(self):
        """Get max parts."""
        return self._max_parts

    @property
    def is_truncated(self):
        """Get is-truncated flag."""
        return self._is_truncated

    @property
    def parts(self):
        """Get parts."""
        return self._parts


class Upload:
    """ Upload information of a multipart upload."""

    def __init__(self, element):
        self._object_name = unquote(findtext(element, "Key", True))
        self._upload_id = findtext(element, "UploadId")
        tag = find(element, "Initiator")
        self._initiator_id = (
            None if tag is None else findtext(tag, "ID")
        )
        self._initiator_name = (
            None if tag is None else findtext(tag, "DisplayName")
        )
        tag = find(element, "Owner")
        self._owner_id = (
            None if tag is None else findtext(tag, "ID")
        )
        self._owner_name = (
            None if tag is None else findtext(tag, "DisplayName")
        )
        self._storage_class = findtext(element, "StorageClass")
        self._initiated_time = findtext(element, "Initiated")
        if self._initiated_time:
            self._initiated_time = strptime_rfc3339(self._initiated_time)

    @property
    def object_name(self):
        """Get object name."""
        return self._object_name

    @property
    def initiator_id(self):
        """Get initiator ID."""
        return self._initiator_id

    @property
    def initator_name(self):
        """Get initiator name."""
        return self._initiator_name

    @property
    def owner_id(self):
        """Get owner ID."""
        return self._owner_id

    @property
    def owner_name(self):
        """Get owner name."""
        return self._owner_name

    @property
    def storage_class(self):
        """Get storage class."""
        return self._storage_class

    @property
    def upload_id(self):
        """Get upload ID."""
        return self._upload_id

    @property
    def initiated_time(self):
        """Get initiated time."""
        return self._initiated_time


class ListMultipartUploadsResult:
    """ListMultipartUploads API result."""

    def __init__(self, response):
        element = ET.fromstring(response.data.decode())
        self._bucket_name = findtext(element, "Bucket")
        self._key_marker = findtext(element, "KeyMarker")
        if self._key_marker:
            self._key_marker = unquote(self._key_marker)
        self._upload_id_marker = findtext(element, "UploadIdMarker")
        self._next_key_marker = findtext(element, "NextKeyMarker")
        if self._next_key_marker:
            self._next_key_marker = unquote(self._next_key_marker)
        self._next_upload_id_marker = findtext(element, "NextUploadIdMarker")
        self._max_uploads = findtext(element, "MaxUploads")
        if self._max_uploads:
            self._max_uploads = int(self._max_uploads)
        self._is_truncated = findtext(element, "IsTruncated")
        self._is_truncated = (
            self._is_truncated is not None and
            self._is_truncated.lower() == "true"
        )
        self._uploads = [Upload(tag) for tag in findall(element, "Upload")]

    @property
    def bucket_name(self):
        """Get bucket name."""
        return self._bucket_name

    @property
    def key_marker(self):
        """Get key marker."""
        return self._key_marker

    @property
    def upload_id_marker(self):
        """Get upload ID marker."""
        return self._upload_id_marker

    @property
    def next_key_marker(self):
        """Get next key marker."""
        return self._next_key_marker

    @property
    def next_upload_id_marker(self):
        """Get next upload ID marker."""
        return self._next_upload_id_marker

    @property
    def max_uploads(self):
        """Get max uploads."""
        return self._max_uploads

    @property
    def is_truncated(self):
        """Get is-truncated flag."""
        return self._is_truncated

    @property
    def uploads(self):
        """Get uploads."""
        return self._uploads
