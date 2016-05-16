import datetime
import json
import logging
from datetime import date
from decimal import Decimal

import copy
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core import mail
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query import QuerySet
from django.http.response import HttpResponse

urls = {}
service_name = 'Service Sample'
service_description = ''
service_version = '1.0'

services = {}

def add_route(url, method):
    urls[url] = method

def add_route_service(url, service, uri):
    urls[url] = {'service' : service, 'uri' : uri}

def add_service(service_name, url):
    services[service_name] = url

def get_service_info(self):
    return {
        'Service Name': self.service_name,
        'Description': self.service_description,
        'Version': self.service_version,
    }


def POST(service_name, action, params):
    request = Request(action, urlencode(params).encode())
    return urlopen(request).read().decode()



def processa_django_request(request):

    # Get the service requested
    action = request.path
    action = urls.get(action, None)

    # PROCESSA OS PARAMETROS
    params = []
    logger = logging.getLogger(__name__)

    if request.method == 'POST':
        params = request.body.decode()
        params = Serializer.json_to_object(params)

    if params != None and not len(params):
        params = []

    if not isinstance(params, list):
        params = [params]



    # Retorno
    result = {"result": "OK",
              "data": ""}
    try:
        if not action:
            result = get_service_info
        elif isinstance(action, dict): # LOCAL SERVICES OR REMOTE SERVICES
            service_call = action['service']
            uri_call = action['uri']
            result = POST(action[service_call], action[uri_call], params)
        else:
            result['data'] = action(*params)

        result = Serializer.object_to_json(result)
    except Exception as e:
        result['result'] = 'ERRO'
        result['data'] = {}
        if not hasattr(e, 'code'):
            e.code = ''

        if not hasattr(e, 'message'):
            e.message = str(e)

        message_detail2 = ''
        if hasattr(e, 'message_detail'):
            message_detail2 = e.message_detail2

        if 'positional arguments but' in e.message \
                or 'must be a sequence, not NoneType' in e.message \
                or 'positional argument' in e.message:
            e.message = 'Number of parameters incorrect'

        result['data']['code'] = e.code
        result['data']['message'] = e.message
        # message_detail = format_exception(e)
        # result['data']['message_detail'] = message_detail
        result['data']['message_detail2'] = message_detail2
        logger.error(e.message)
    finally:
        response = HttpResponse()
        response.status_code = 200
        response.write(result)

        return response

def config_classes(classes=[], methods=[]):
    """
    This method injects basic functions for djgando model or others functions passed by params
    :param self:
    :param classes:
    :param methods:
    :return:
    """
    if not methods:
        methods = [save, delete, list]

    for classe in classes:
        for method in methods:
            setattr(classe, method.__name__, method)


def save(self, data=None):
    if data:
        self.__dict__ = data

    try:
        self.full_clean()

    except ValidationError as e:
        message = e.message_dict
        raise Exception('FIELDS_VALIDATION', message)

    super(self.__class__, self).save()
    return self


def delete(classe, ids):
    objs = classe.objects.filter(id__in=[ids])
    deleted_records = objs.delete()
    return 'Excluido {0} registros'.format(deleted_records)


def toDjangoFilter(self, filter):
    queryFilter = {}
    # Filtro
    for where in filter.get('where', []):

        field = where.get('field', '')
        value = where.get('value', '')
        condition = ''
        where = []
        # veja se tem asterisco na consulta
        if isinstance(value, str):
            if '*' in value:
                values = value.split('*')
                for v in values:
                    if v:
                        condition = '__contains'
                        value = v
            else:
                condition = '__startswith'

        queryFilter[field + condition] = value

    query = self.__class__.objects.filter(**queryFilter)

    if filter.get('select', []):
        query = query.values(*filter.get('select', []))
    elif self.FIELDS:
        query = query.values(*self.FIELDS)

    query = query.distinct()
    return query


def query(classe, filter=None):
    if filter:
        if isinstance(filter, dict):
            return toDjangoFilter(filter)
            # return self.__class__.objects.filter(**filter).all()

    return classe.objects.filter(**filter).all()


def send_mail(subject='', body='', from_email=None, to=None, bcc=None,
              connection=None, attachments=None, headers=None, cc=None,
              reply_to=None, html=True):
    if not isinstance(to, (list, tuple)):
        email_to = [to]

    conn = mail.get_connection()
    msg = mail.EmailMessage(subject, body, from_email, to,
                            connection=conn)
    if html:
        msg.content_subtype = "html"

    try:
        msg.send()
    except Exception as e:
        raise Exception(e)



def del_none(d):
    if isinstance(d, dict):
        return dict((k, v) for k, v in d.items() if v and not k.startswith('_'))

    return None


def normalize_objects(obj):
    def queryset_to_list(queryset):
        retorno = []
        obj = list(queryset)

        for m in obj:
            model = None
            if isinstance(m, models.Model):
                model = model_to_dict(m)
            else:
                model = m

            model = del_none(model)
            retorno.append(model)
        return retorno

    def model_to_dict(obj):
        obj = obj.__dict__
        if hasattr(obj, '_state'):
            del obj['_state']
        obj = del_none(obj)
        obj = normalize_objects(obj)
        return obj

    def object_to_dict(obj):
        if hasattr(obj, '__dict__'):
            return normalize_objects(obj.__dict__)
        return obj

    if isinstance(obj, QuerySet):
        obj = queryset_to_list(obj)

    elif isinstance(obj, models.Model):
        obj = model_to_dict(obj)

    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (QuerySet, models.Model, dict, list, type)) or hasattr(value, '__dict__'):
                obj[key] = normalize_objects(value)

    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            if isinstance(value, (QuerySet, models.Model, dict, list, type)) or hasattr(value, '__dict__'):
                obj[index] = normalize_objects(value)

    elif isinstance(obj, type):  # if the object is a type(class), if it's not an object
        obj = None

    obj = object_to_dict(obj)
    if not isinstance(obj, (str, int, float, dict, list, bool)) and obj != None:
        raise ValueError(
            'Could not convert the object {0}. Expected :  str,int,float,dict,list,bool but got : {1}'.format(
                obj.__name__), type(obj))

    return obj


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        """
        default method is used if there is an unexpected object type
        in our example obj argument will be Decimal('120.50') and datetime
        in this encoder we are converting all Decimal to float and datetime to str
        """
        if isinstance(obj, (datetime, date, datetime.time)):
            obj = str(obj)
        elif isinstance(obj, Decimal):
            obj = float(obj)
        elif obj == None:
            return None
        else:
            obj = super(JsonEncoder, self).default(obj)
        return obj


class Serializer():
    @classmethod
    def json_to_object(self, json):
        if not json.strip():
            return None

        obj = toObj(json)
        return obj

    @classmethod
    def object_to_json(self, obj):
        newobj = copy.deepcopy(obj)
        newobj = normalize_objects(newobj)
        newobj = toJson(newobj)
        return newobj


def toJson(obj):
    if hasattr(obj, '__dict__'):
        return json.dumps(obj.__dict__, cls=JsonEncoder).encode('utf8')
    else:
        return json.dumps(obj, ensure_ascii=False, cls=JsonEncoder, sort_keys=True)


def toObj(jsonString):
    try:
        obj = json.loads(jsonString, parse_float=Decimal)
        return obj
    except Exception as e:
        raise (e)
