import json
import re
import sys
import xml.etree.ElementTree as etree

import requests
from requests.auth import HTTPDigestAuth

HOST = '192.168.8.74'
PASSWORD = 'vw8LN7L76Qv?'
USER = 'Service'

# found here: http://<WINDHAGER IP>/res/xml/VarIdentTexte_de.xml
var_ids_xml = None
with open('VarIdentTexte_de.xml', 'r', encoding='UTF-8') as file:
    var_ids_xml = etree.fromstring(file.read())

# found here: http://<WINDHAGER IP>/res/xml/EbenenTexte_de.xml
ebenen_xml = None
with open('EbenenTexte_de.xml', 'r', encoding='UTF-8') as file:
    ebenen_xml = etree.fromstring(file.read())

def find_ebene(fcttype, id):
    e = ebenen_xml.find(f'fcttyp[@id=\"{fcttype}\"]/ebene[@id=\"{id}\"]')
    if e is not None:
        if e.text is not None:
            return e.text.strip().replace('.', '')
    return 'unbekannt'

def find_var(gn, mn):
    e = var_ids_xml.find(f'gn[@id=\"{gn}\"]/mn[@id=\"{mn}\"]')
    if e is not None:
        if e.text is not None:
            return e.text.strip().replace('.', '')
    return 'unbekannt'

def get(api: str = ''):
    response = requests.get(f'http://{HOST}/api/1.0/lookup{api}', auth = HTTPDigestAuth(USER, PASSWORD), timeout=10)
    if response.status_code != 200:
        raise Exception
    try:
        return json.loads(response.text)
    except:
        return response.text

def main():
    """ Recursive scan for all OIDS. """
    nodeNames = []
    fctNames = []

    # Get root node - should always be /1
    subnetIds = get()
    if not subnetIds:
        print('No subnetIds found!')
        return None

    with open('oids_metrics.txt', 'w', encoding='UTF-8') as file:
        # Iterate over all subnets
        for subnet in subnetIds:
            nodeIds = []
            nodeResp = get(f'/{subnet}')
            for resp in nodeResp:
                if 'nodeId' in resp:
                    nodeIds.append(resp['nodeId'])
                if 'name' in resp:
                    nodeNames.append({
                        'id' : resp['nodeId'],
                        'name' : resp['name']
                    })

            # Iterate over all nodes
            for node in nodeIds:
                fctIds = []
                fctResp = get(f'/{subnet}/{node}')
                if not 'functions' in fctResp:
                    print(f'Malformed fctResp, no functions found: {fctResp}')
                    return None
                for resp in fctResp['functions']:
                    if 'fctId' in resp:
                        fctIds.append(resp['fctId'])
                    if 'name' in resp:
                        fctNames.append({
                            'id' : resp['fctId'],
                            'nodeid' : node,
                            'name' : resp['name'],
                            'type' : resp['fctType']
                        })

                # Iterate over all functions
                for fct in fctIds:
                    subfctIds = []
                    try:
                        subfctResp = get(f'/{subnet}/{node}/{fct}')
                    except:
                        continue
                    for resp in subfctResp:
                        if 'id' in resp:
                            subfctIds.append(resp['id'])

                    # Iterate over all subfunctions
                    for subfct in subfctIds:

                        type = ''
                        for fnctn in fctNames:
                            if fnctn['id'] == fct and fnctn['nodeid'] == node:
                                type = fnctn['type']
                                break

                        ebene = find_ebene(type, subfct)

                        try:
                            nvResp = get(f'/{subnet}/{node}/{fct}/{subfct}')

                            node_name = 'unbekannt'
                            for n in nodeNames:
                                if n['id'] == node:
                                    node_name = n['name'].strip()
                                    break

                            fct_name = 'unbekannt'
                            for f in fctNames:
                                if f['id'] == fct and f['nodeid'] == node:
                                    fct_name = f['name'].strip()
                                    break
                        except:
                            continue

                        for nv in nvResp:
                            var = 'unbekannt'
                            oid = 'unbekannt'
                            if 'name' in nv:
                                gn, mn = nv['name'].split('-')
                                gn = int(gn)
                                mn = int(mn)
                                var = find_var(gn, mn)

                            if 'OID' in nv:
                                oid = nv['OID']

                            # convert all oids names to a usable metric path for graphite
                            special_char_map = {ord('ä'):'ae', ord('ü'):'ue', ord('ö'):'oe', ord('ß'):'ss', ord(' '):'_'}
                            graphite_metric_path = f'windhager.{node_name}.{fct_name}.{ebene}.{var}'.translate(special_char_map)
                            graphite_metric_path = re.sub('[\'!@#$\-/\s+]', '', graphite_metric_path)

                            datapoint_path = f'{subnet}/{node}/{fct}/{subfct}'

                            file.write(f'{graphite_metric_path};{datapoint_path};{oid}\n')

if __name__ == '__main__':
    main()

