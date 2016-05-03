import datetime
import json
from datetime import date
from decimal import Decimal

import copy
from pyutil.django import HttpResponse
from pyutil.django import QuerySet
from pyutil.django import models


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



def processa_django_request(request, action):


    # PROCESSA OS PARAMETROS
    params = []
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
        result['data'] = action(*params)
        result = Serializer.object_to_json(result)

        response = HttpResponse()
        response.status_code = 200
        response.write(result)

        return response
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
        return result
