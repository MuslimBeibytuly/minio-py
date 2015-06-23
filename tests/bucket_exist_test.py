# Minimal Object Storage Library, (C) 2015 Minio, Inc.
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
from unittest import TestCase

import mock
from nose.tools import raises, eq_

from minio import minio
from minio.exceptions import BucketExistsException, InvalidBucketNameException
from .minio_mocks import MockResponse

__author__ = 'minio'


class BucketExists(TestCase):
    @raises(TypeError)
    def test_bucket_is_string(self):
        client = minio.Minio('http://localhost:9000')
        client.bucket_exists(1234)

    @raises(ValueError)
    def test_bucket_is_not_empty_string(self):
        client = minio.Minio('http://localhost:9000')
        client.bucket_exists('  \t \n  ')

    @mock.patch('requests.get')
    def test_bucket_exists_works(self, mock_request):
        mock_request.return_value = MockResponse('GET', 'http://localhost:9000/hello', {}, 206)
        client = minio.Minio('http://localhost:9000')
        result = client.bucket_exists('hello')
        eq_(True, result)

    @mock.patch('requests.get')
    def test_bucket_exists_throws_fail(self, mock_request):
        mock_request.return_value = MockResponse('PUT', 'http://localhost:9000/hello', {}, 409)
        client = minio.Minio('http://localhost:9000')
        result = client.bucket_exists('hello')
        eq_(False, result)

    @mock.patch('requests.get')
    @raises(InvalidBucketNameException)
    def test_bucket_exists_invalid_name(self, mock_request):
        mock_request.return_value = MockResponse('PUT', 'http://localhost:9000/hello', {}, 400)
        client = minio.Minio('http://localhost:9000')
        client.bucket_exists('1234')
