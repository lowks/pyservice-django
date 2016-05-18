from pyservice_django.pyservice_django import post


def test_POST():
    url = 'https://sigeflex-service-cep.appspot.com/consulta_cidade'
    params = ["Moss"]
    assert post(url, params)!=None

