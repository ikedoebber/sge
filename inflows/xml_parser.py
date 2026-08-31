import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation


# Namespaces comuns usados em XMLs de NFe
NFE_NAMESPACES = {
    'nfe': 'http://www.portalfiscal.inf.br/nfe',
    'nfe310': 'http://www.portalfiscal.inf.br/nfe',
    'nfe400': 'http://www.portalfiscal.inf.br/nfe',
}


def parse_nfe_xml(xml_content):
    """
    Analisa um XML e tenta extrair itens/produtos.
    
    Suporta:
    - NFe (Nota Fiscal Eletronica) com namespace padrao
    - NFe sem namespace
    - XMLs genericos com estrutura de itens
    
    Retorna um dicionario com:
    - emitente: informacoes do fornecedor (se encontrado)
    - itens: lista de dicionarios com os produtos
    - erro: mensagem de erro (se houver)
    - debug: informacoes de debug para troubleshooting
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return {
            'erro': f'Erro ao analisar o XML: {str(e)}',
            'emitente': None,
            'itens': [],
            'debug': 'Arquivo nao e um XML valido.'
        }
    
    # Info de debug
    root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
    ns_uri = root.tag.split('}')[0].lstrip('{') if '}' in root.tag else None
    debug_info = f'Raiz: <{root_tag}>'
    if ns_uri:
        debug_info += f' | Namespace: {ns_uri}'
    
    # Detectar namespace do documento
    ns = _detect_namespace(root)
    
    # Extrair informacoes do emitente (fornecedor)
    emitente = _extract_emitente(root, ns)
    
    # Extrair itens/produtos
    itens = _extract_itens(root, ns)
    
    # Se nao encontrou itens no padrao NFe, tentar estruturas genericas
    if not itens:
        itens = _extract_generic_items(root)
    
    if not itens:
        # Montar mensagem de erro detalhada
        all_tags = [elem.tag.split('}')[-1] for elem in root.iter()]
        tags_unicas = list(set(all_tags))[:20]
        
        erro_msg = 'Nenhum item/produto encontrado no XML.'
        erro_msg += '\n\nEste arquivo nao parece ser uma Nota Fiscal Eletronica (NFe) valida.'
        erro_msg += f'\n\nEstrutura encontrada: <{root_tag}>'
        erro_msg += f'\nTags encontradas: {", ".join(tags_unicas)}'
        erro_msg += '\n\nPara importar entradas em estoque, o XML deve ser uma NFe com os campos:'
        erro_msg += '\n- <det> com <prod> dentro (itens da nota)'
        erro_msg += '\n- <cProd> (codigo), <xProd> (descricao), <qCom> (quantidade), <vUnCom> (valor unitario)'
        
        return {
            'erro': erro_msg,
            'emitente': emitente,
            'itens': [],
            'debug': debug_info,
        }
    
    return {
        'erro': None,
        'emitente': emitente,
        'itens': itens,
        'debug': debug_info,
    }


def _detect_namespace(root):
    """Detecta o namespace usado no XML da NFe."""
    tag = root.tag
    if '{' in tag:
        ns_uri = tag.split('}')[0].lstrip('{')
        return {'nfe': ns_uri}
    return NFE_NAMESPACES


def _extract_emitente(root, ns):
    """Extrai informacoes do emitente (fornecedor) da NFe."""
    emit = root.find('.//nfe:emit', ns)
    if emit is None:
        emit = root.find('.//emit')
    
    if emit is None:
        return None
    
    cnpj = _get_text(emit, 'nfe:CNPJ', ns) or _get_text(emit, 'CNPJ', ns)
    razao_social = _get_text(emit, 'nfe:xNome', ns) or _get_text(emit, 'xNome', ns)
    nome_fantasia = _get_text(emit, 'nfe:xFant', ns) or _get_text(emit, 'xFant', ns)
    ie = _get_text(emit, 'nfe:IE', ns) or _get_text(emit, 'IE', ns)
    
    # Endereco do emitente
    ender = emit.find('nfe:enderEmit', ns) or emit.find('enderEmit')
    endereco = None
    if ender is not None:
        logradouro = _get_text(ender, 'nfe:xLgr', ns) or _get_text(ender, 'xLgr', ns)
        numero = _get_text(ender, 'nfe:nro', ns) or _get_text(ender, 'nro', ns)
        complemento = _get_text(ender, 'nfe:xCpl', ns) or _get_text(ender, 'xCpl', ns)
        bairro = _get_text(ender, 'nfe:xBairro', ns) or _get_text(ender, 'xBairro', ns)
        cidade = _get_text(ender, 'nfe:xMun', ns) or _get_text(ender, 'xMun', ns)
        cod_municipio = _get_text(ender, 'nfe:cMun', ns) or _get_text(ender, 'cMun', ns)
        uf = _get_text(ender, 'nfe:UF', ns) or _get_text(ender, 'UF', ns)
        cep = _get_text(ender, 'nfe:CEP', ns) or _get_text(ender, 'CEP', ns)
        telefone = _get_text(ender, 'nfe:fone', ns) or _get_text(ender, 'fone', ns)
        pais = _get_text(ender, 'nfe:xPais', ns) or _get_text(ender, 'xPais', ns)
        cod_pais = _get_text(ender, 'nfe:cPais', ns) or _get_text(ender, 'cPais', ns)
        email = _get_text(ender, 'nfe:email', ns) or _get_text(ender, 'email', ns)
        
        # Montar endereco completo
        parts = [p for p in [logradouro, numero] if p]
        complemento_str = None
        if complemento:
            complemento_str = complemento
        
        endereco = {
            'logradouro': ', '.join(parts) if parts else None,
            'complemento': complemento_str,
            'bairro': bairro,
            'cidade': cidade,
            'cod_municipio': cod_municipio,
            'uf': uf,
            'cep': cep,
            'telefone': telefone,
            'pais': pais,
            'cod_pais': cod_pais,
            'email': email,
        }
    
    return {
        'cnpj': cnpj,
        'razao_social': razao_social,
        'nome_fantasia': nome_fantasia,
        'ie': ie,
        'endereco': endereco,
    }


def _extract_itens(root, ns):
    """Extrai todos os itens/produtos da NFe."""
    itens = []
    
    # Buscar todos os elementos 'det' (detalhamento de itens)
    dets = root.findall('.//nfe:det', ns)
    if not dets:
        dets = root.findall('.//det')
    
    for det in dets:
        prod = det.find('nfe:prod', ns) or det.find('prod')
        if prod is None:
            continue
        
        # Extrair campos do produto
        cprod = _get_text(prod, 'nfe:cProd', ns) or _get_text(prod, 'cProd', ns)
        cean = _get_text(prod, 'nfe:cEAN', ns) or _get_text(prod, 'cEAN', ns)
        xprod = _get_text(prod, 'nfe:xProd', ns) or _get_text(prod, 'xProd', ns)
        ncm = _get_text(prod, 'nfe:NCM', ns) or _get_text(prod, 'NCM', ns)
        ucom = _get_text(prod, 'nfe:uCom', ns) or _get_text(prod, 'uCom', ns)
        qcom = _get_text(prod, 'nfe:qCom', ns) or _get_text(prod, 'qCom', ns)
        vuncom = _get_text(prod, 'nfe:vUnCom', ns) or _get_text(prod, 'vUnCom', ns)
        vprod = _get_text(prod, 'nfe:vProd', ns) or _get_text(prod, 'vProd', ns)
        cfop = _get_text(prod, 'nfe:CFOP', ns) or _get_text(prod, 'CFOP', ns)
        
        # Extrair valores adicionais se existirem
        vfrete = _get_text(prod, 'nfe:vFrete', ns) or _get_text(prod, 'vFrete', ns)
        vseg = _get_text(prod, 'nfe:vSeg', ns) or _get_text(prod, 'vSeg', ns)
        vdesc = _get_text(prod, 'nfe:vDesc', ns) or _get_text(prod, 'vDesc', ns)
        
        # Converter quantidades e valores para Decimal
        quantidade = _to_decimal(qcom)
        valor_unitario = _to_decimal(vuncom)
        valor_total = _to_decimal(vprod)
        
        itens.append({
            'codigo': cprod,
            'ean': cean,
            'descricao': xprod,
            'ncm': ncm,
            'unidade': ucom,
            'quantidade': quantidade,
            'valor_unitario': valor_unitario,
            'valor_total': valor_total,
            'cfop': cfop,
            'frete': vfrete,
            'seguro': vseg,
            'desconto': vdesc,
        })
    
    return itens


def _extract_generic_items(root):
    """
    Tenta extrair itens de XMLs genericos que nao sao NFe.
    Procura por elementos que contenham campos parecidos com produtos.
    """
    itens = []
    
    # Possiveis nomes de elementos que podem conter itens
    item_tags = ['item', 'produto', 'product', 'detalhe', 'detail', 'linha', 'line', 'mercadoria', 'goods', 'merchandise']
    name_tags = ['nome', 'name', 'descricao', 'description', 'titulo', 'title', 'xProd', 'descricaoProduto', 'productName', 'nomeProduto', 'nome_produto', 'descricao_produto', 'descrição']
    qty_tags = ['quantidade', 'quantity', 'qtd', 'qty', 'qCom', 'qtde', 'quantidadeProduto', 'quantidade_produto', 'qtdade', 'amount']
    price_tags = ['preco', 'price', 'valor', 'value', 'vUnCom', 'precoUnitario', 'unitPrice', 'precoUnit', 'valorUnitario', 'unit_price', 'preco_produto']
    cost_tags = ['preco_custo', 'custo', 'cost', 'costPrice', 'precoCusto', 'custoUnitario', 'custo_unitario', 'purchasePrice', 'preco_compra', 'precoCompra', 'valorCusto', 'valor_custo']
    sale_tags = ['preco_venda', 'venda', 'sale', 'sellingPrice', 'salePrice', 'precoVenda', 'precoVendaProduto', 'valorVenda', 'valor_venda', 'retailPrice', 'preco_sugerido', 'precoSugerido']
    code_tags = ['codigo', 'code', 'cProd', 'id', 'sku', 'codigoProduto', 'codigo_produto', 'codeProduct', 'productCode', 'barCode', 'codigoBarras', 'codigo_barras', 'ean', 'gtin']
    
    # Buscar todos os elementos e agrupar por tag case-insensitive
    all_elements = {}
    for elem in root.iter():
        tag_lower = elem.tag.lower()
        if tag_lower not in all_elements:
            all_elements[tag_lower] = []
        all_elements[tag_lower].append(elem)
    
    # Buscar por itens em diferentes estruturas
    for item_tag in item_tags:
        item_tag_lower = item_tag.lower()
        items = all_elements.get(item_tag_lower, [])
        
        for item_elem in items:
            name = _find_field(item_elem, name_tags)
            qty_str = _find_field(item_elem, qty_tags)
            code = _find_field(item_elem, code_tags)
            
            # Buscar preco de custo e venda
            custo_str = _find_field(item_elem, cost_tags)
            venda_str = _find_field(item_elem, sale_tags)
            
            # Se tem preco_custo, usar como valor_unitario
            if custo_str:
                price_str = custo_str
            else:
                price_str = _find_field(item_elem, price_tags)
            
            if name:  # Se encontrou pelo menos o nome
                quantidade = _to_decimal(qty_str) or Decimal('1')
                valor_unitario = _to_decimal(price_str) or Decimal('0')
                valor_total = quantidade * valor_unitario
                
                itens.append({
                    'codigo': code,
                    'ean': None,
                    'descricao': name,
                    'ncm': None,
                    'unidade': 'UN',
                    'quantidade': quantidade,
                    'valor_unitario': valor_unitario,
                    'valor_total': valor_total,
                    'cfop': None,
                    'frete': None,
                    'seguro': None,
                    'desconto': None,
                    'preco_custo': _to_decimal(custo_str),
                    'preco_venda': _to_decimal(venda_str),
                })
    
    # Se ainda nao encontrou, varrer todos os elementos recursivamente
    if not itens:
        itens = _recursive_item_search(root)
    
    return itens


def _recursive_item_search(element):
    """Busca recursiva por elementos que parecam itens/produtos."""
    itens = []
    
    name_tags = ['nome', 'name', 'descricao', 'description', 'titulo', 'title', 'productName', 'nomeProduto']
    qty_tags = ['quantidade', 'quantity', 'qtd', 'qty', 'qtdade', 'amount']
    price_tags = ['preco', 'price', 'valor', 'value', 'precoUnitario', 'unitPrice']
    cost_tags = ['preco_custo', 'custo', 'cost', 'costPrice', 'precoCusto', 'preco_compra']
    sale_tags = ['preco_venda', 'venda', 'sale', 'sellingPrice', 'salePrice', 'precoVenda']
    
    for child in element:
        name = _find_field(child, name_tags)
        qty_str = _find_field(child, qty_tags)
        custo_str = _find_field(child, cost_tags)
        venda_str = _find_field(child, sale_tags)
        
        if custo_str:
            price_str = custo_str
        else:
            price_str = _find_field(child, price_tags)
        
        if name and qty_str:
            quantidade = _to_decimal(qty_str) or Decimal('1')
            valor_unitario = _to_decimal(price_str) or Decimal('0')
            valor_total = quantidade * valor_unitario
            
            itens.append({
                'codigo': None,
                'ean': None,
                'descricao': name,
                'ncm': None,
                'unidade': 'UN',
                'quantidade': quantidade,
                'valor_unitario': valor_unitario,
                'valor_total': valor_total,
                'cfop': None,
                'frete': None,
                'seguro': None,
                'desconto': None,
                'preco_custo': _to_decimal(custo_str),
                'preco_venda': _to_decimal(venda_str),
            })
        else:
            # Recursar nos filhos
            itens.extend(_recursive_item_search(child))
    
    return itens


def _find_field(element, possible_tags):
    """Busca o texto de um elemento tentando varios nomes possiveis (case-insensitive)."""
    for tag in possible_tags:
        # Tentar com o tag original
        child = element.find(tag)
        if child is None:
            child = element.find(f'.//{tag}')
        
        # Se nao encontrou, tentar com primeira letra maiuscula
        if child is None and tag:
            capitalized = tag[0].upper() + tag[1:]
            child = element.find(capitalized)
            if child is None:
                child = element.find(f'.//{capitalized}')
        
        # Se ainda nao encontrou, tentar com todas maiusculas
        if child is None and tag:
            upper = tag.upper()
            child = element.find(upper)
            if child is None:
                child = element.find(f'.//{upper}')
        
        # Se ainda nao encontrou, tentar com todas minusculas
        if child is None and tag:
            lower = tag.lower()
            child = element.find(lower)
            if child is None:
                child = element.find(f'.//{lower}')
        
        # Se ainda nao encontrou, buscar todos os elementos e comparar case-insensitive
        if child is None and tag:
            for elem in element.iter():
                elem_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if elem_tag.lower() == tag.lower() and elem.text:
                    return elem.text.strip()
        
        if child is not None and child.text:
            return child.text.strip()
    return None


def _to_decimal(value):
    """Converte um valor para Decimal, retornando None se falhar."""
    if not value:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _get_text(element, tag, ns):
    """Busca o texto de um subelemento, tentando com e sem namespace."""
    if element is None:
        return None
    
    child = element.find(tag, ns)
    if child is None and ':' in tag:
        simple_tag = tag.split(':')[1]
        child = element.find(simple_tag)
    
    return child.text.strip() if child is not None and child.text else None


def format_cpf_cnpj(value):
    """Formata CPF ou CNPJ para exibicao."""
    if not value:
        return '-'
    
    digits = ''.join(filter(str.isdigit, value))
    
    if len(digits) == 11:
        return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
    elif len(digits) == 14:
        return f'{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}'
    
    return value
