from decimal import Decimal
from rest_framework import generics
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, FormView
from django.contrib import messages
from django.shortcuts import redirect, render
from . import models, forms, serializers
from .xml_parser import parse_nfe_xml, format_cpf_cnpj
from products.models import Product
from suppliers.models import Supplier
from brands.models import Brand
from categories.models import Category


def _decimals_to_floats(items):
    """Converte objetos Decimal para float em uma lista de dicts do XML."""
    converted = []
    for item in items:
        new_item = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                new_item[key] = float(value)
            else:
                new_item[key] = value
        converted.append(new_item)
    return converted


def _find_or_create_supplier(emitente):
    """
    Busca fornecedor existente pelo nome ou cria um novo.
    Retorna (supplier, created).
    Preenche todos os campos disponiveis na NFe.
    """
    if not emitente:
        return None, False

    razao = emitente.get('razao_social', '')
    cnpj = emitente.get('cnpj', '')

    # Tentar buscar por nome exato
    if razao:
        supplier = Supplier.objects.filter(name__iexact=razao).first()
        if supplier:
            return supplier, False

    # Tentar buscar por nome parecido (contem)
    if razao:
        supplier = Supplier.objects.filter(name__icontains=razao).first()
        if supplier:
            return supplier, False

    # Criar novo fornecedor com todos os dados da NFe
    nome = razao or emitente.get('nome_fantasia', 'Fornecedor NFe')
    endereco = emitente.get('endereco', {})
    
    # Formatar CNPJ se existir
    cnpj_formatado = format_cpf_cnpj(cnpj) if cnpj else None

    # Montar endereco completo
    address_parts = []
    if endereco:
        if endereco.get('logradouro'):
            address_parts.append(endereco['logradouro'])
        if endereco.get('complemento'):
            address_parts.append(endereco['complemento'])
        if endereco.get('bairro'):
            address_parts.append(endereco['bairro'])

    supplier = Supplier.objects.create(
        name=nome,
        person_type='pj',
        cpf_cnpj=cnpj_formatado,
        email=endereco.get('email') if endereco else None,
        phone=endereco.get('telefone') if endereco else None,
        address=', '.join(address_parts) if address_parts else None,
        city=endereco.get('cidade') if endereco else None,
        state=endereco.get('uf') if endereco else None,
        notes=f'Importado automaticamente via NFe.\nCNPJ: {cnpj_formatado}' if cnpj_formatado else None,
    )
    return supplier, True


def _find_or_create_product(item_xml, consignment_mode=False, consignment_supplier=None, consignment_return_date=None):
    """
    Busca produto existente pelo codigo ou descricao ou cria um novo.
    Retorna (product, created).
    """
    codigo = item_xml.get('codigo', '')
    descricao = item_xml.get('descricao', '')
    ean = item_xml.get('ean', '')
    valor_unitario = item_xml.get('valor_unitario', 0)
    preco_custo = item_xml.get('preco_custo')
    preco_venda = item_xml.get('preco_venda')

    # Tentar buscar por serie_number (codigo do item no XML)
    if codigo:
        product = Product.objects.filter(serie_number=codigo).first()
        if product:
            return product, False

    # Tentar buscar por titulo exato
    if descricao:
        product = Product.objects.filter(title__iexact=descricao).first()
        if product:
            return product, False

    # Tentar buscar por titulo parecido
    if descricao:
        product = Product.objects.filter(title__icontains=descricao).first()
        if product:
            return product, False

    # Criar novo produto com categoria e marca padrao
    category, _ = Category.objects.get_or_create(
        name='Importado NFe',
        defaults={'description': 'Produtos importados automaticamente via XML de NFe'}
    )
    brand, _ = Brand.objects.get_or_create(
        name='Sem Marca',
        defaults={'description': 'Marca padrao para produtos importados'}
    )

    # Definir precos: usar preco_custo/preco_venda se existirem, senao valor_unitario
    if preco_custo:
        cost = float(preco_custo)
    else:
        cost = float(valor_unitario)
    
    if preco_venda:
        selling = float(preco_venda)
    else:
        selling = cost * 1.3  # 30% de markup padrao

    # Definir tipo de estoque
    stock_type = 'consignado' if consignment_mode else 'proprio'

    product = Product.objects.create(
        title=descricao or f'Produto NFe {codigo}',
        category=category,
        brand=brand,
        description=f'Importado automaticamente via NFe.\nEAN: {ean}' if ean else None,
        serie_number=codigo or None,
        cost_price=cost,
        selling_price=selling,
        quantity=0,
        stock_type=stock_type,
        consignment_supplier=consignment_supplier if consignment_mode else None,
        consignment_return_date=consignment_return_date if consignment_mode else None,
    )
    return product, True


class InflowListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Inflow
    template_name = 'inflow_list.html'
    context_object_name = 'inflows'
    paginate_by = 10
    permission_required = 'inflows.view_inflow'

    def get_queryset(self):
        queryset = super().get_queryset()
        product = self.request.GET.get('product')

        if product:
            queryset = queryset.filter(product__title__icontains=product)

        return queryset


class InflowCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = models.Inflow
    template_name = 'inflow_create.html'
    form_class = forms.InflowForm
    success_url = reverse_lazy('inflow_list')
    permission_required = 'inflows.add_inflow'

    def form_valid(self, form):
        response = super().form_valid(form)
        unit_cost = form.cleaned_data.get('unit_cost')
        selling_price = form.cleaned_data.get('selling_price')
        product = self.object.product
        updated_fields = []
        if unit_cost:
            product.cost_price = unit_cost
            updated_fields.append('cost_price')
        if selling_price:
            product.selling_price = selling_price
            updated_fields.append('selling_price')
        if updated_fields:
            product.save(update_fields=updated_fields)
        return response


class InflowDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Inflow
    template_name = 'inflow_detail.html'
    permission_required = 'inflows.view_inflow'


class InflowXMLUploadView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    View para upload e importacao automatica de XML de NFe.
    
    Fluxo:
    1. GET: Exibe formulario de upload
    2. POST sem confirm_import: Analisa XML e mostra preview
    3. POST com confirm_import: Cria fornecedor, produtos e entradas automaticamente
    """
    
    template_name = 'inflow_xml_upload.html'
    form_class = forms.InflowXMLUploadForm
    success_url = reverse_lazy('inflow_list')
    permission_required = 'inflows.add_inflow'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all()
        context['suppliers'] = Supplier.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        # Verificar se e uma requisicao de confirmacao (itens ja parseados)
        if 'confirm_import' in request.POST:
            return self._process_confirmation(request)
        
        # Caso contrario, processar o upload do XML
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        xml_file = form.cleaned_data['xml_file']
        
        # Ler o conteudo do arquivo
        try:
            xml_content = xml_file.read().decode('utf-8')
        except UnicodeDecodeError:
            try:
                xml_file.seek(0)
                xml_content = xml_file.read().decode('latin-1')
            except Exception:
                messages.error(self.request, 'Erro ao ler o arquivo XML. Verifique a codificacao do arquivo.')
                return self.form_invalid(form)
        
        # Analisar o XML
        result = parse_nfe_xml(xml_content)
        
        if result['erro']:
            messages.error(self.request, result['erro'])
            return self.form_invalid(form)
        
        # Converter Decimals para floats
        items_converted = _decimals_to_floats(result['itens'])
        
        # Pre-processar: buscar/criar fornecedor e produtos para o preview
        emitente = result['emitente']
        supplier, supplier_created = _find_or_create_supplier(emitente)
        
        # Verificar se o fornecedor e de consignacao
        is_consignment_supplier = supplier.is_consignment_supplier if supplier else False
        
        preview_items = []
        for item in items_converted:
            product, product_created = _find_or_create_product(item)
            preview_items.append({
                'xml': item,
                'product': product,
                'product_created': product_created,
            })
        
        # Salvar dados na sessao para a confirmacao
        self.request.session['xml_items'] = items_converted
        self.request.session['xml_emitente'] = emitente
        self.request.session['supplier_id'] = supplier.id if supplier else None
        self.request.session['supplier_created'] = supplier_created
        self.request.session['product_ids'] = [
            {'id': p['product'].id, 'created': p['product_created']} 
            for p in preview_items
        ]
        self.request.session['is_consignment_supplier'] = is_consignment_supplier
        # Forcar save da sessao (render() nao salva automaticamente)
        self.request.session.save()
        
        # Renderizar preview
        total_value = sum(item.get('valor_total', 0) for item in items_converted)
        context = {
            'preview_items': preview_items,
            'emitente': emitente,
            'supplier': supplier,
            'supplier_created': supplier_created,
            'total_items': len(items_converted),
            'total_value': total_value,
            'processing': True,
            'all_suppliers': Supplier.objects.all().order_by('name'),
            'all_brands': Brand.objects.all().order_by('name'),
        }
        
        return render(self.request, 'inflow_xml_upload.html', context)
    
    def _process_confirmation(self, request):
        """Processa a confirmacao - cria as entradas em estoque."""
        product_ids = request.session.get('product_ids', [])
        xml_items = request.session.get('xml_items', [])
        
        if not product_ids or not xml_items:
            messages.error(request, 'Dados da importacao expirados. Faca o upload novamente.')
            return redirect('inflow_xml_upload')
        
        # Ler fornecedor e marca selecionados no preview (opcionais)
        selected_supplier_id = request.POST.get('supplier_id', '').strip()
        selected_brand_id = request.POST.get('brand_id', '').strip()
        
        # Ler dados de consignacao
        consignment_mode = request.POST.get('consignment_mode') == 'true'
        consignment_return_date_str = request.POST.get('consignment_return_date', '').strip()
        
        consignment_return_date = None
        if consignment_return_date_str:
            try:
                from datetime import datetime
                consignment_return_date = datetime.strptime(consignment_return_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        supplier = None
        if selected_supplier_id:
            try:
                supplier = Supplier.objects.get(id=selected_supplier_id)
            except (Supplier.DoesNotExist, ValueError):
                supplier = None
        
        # Se nao selecionou nenhum, usar o da sessao
        if not supplier:
            session_supplier_id = request.session.get('supplier_id')
            if session_supplier_id:
                try:
                    supplier = Supplier.objects.get(id=session_supplier_id)
                except Supplier.DoesNotExist:
                    supplier = None
        
        # Se ainda nao tem fornecedor, criar um padrao (obrigatorio para Inflow)
        if not supplier:
            supplier, _ = Supplier.objects.get_or_create(
                name='Sem Fornecedor',
                defaults={'notes': 'Fornecedor padrao para entradas importadas'}
            )
        
        # Marca selecionada para novos produtos (opcional)
        brand = None
        if selected_brand_id:
            try:
                brand = Brand.objects.get(id=selected_brand_id)
            except (Brand.DoesNotExist, ValueError):
                brand = None
        
        # Criar entradas para cada item
        created_count = 0
        errors = []
        
        for i, item in enumerate(xml_items):
            if i >= len(product_ids):
                break
            
            product_id = product_ids[i]['id']
            quantity = item.get('quantidade', 0)
            
            if quantity <= 0:
                continue
            
            try:
                product = Product.objects.get(id=product_id)
                # Se uma marca foi selecionada e o produto e novo, atualizar a marca
                if brand and product_ids[i].get('created'):
                    product.brand = brand
                
                # Atualizar precos do produto - sempre sobrescrever com valores do XML
                valor_unitario = item.get('valor_unitario', 0)
                preco_custo = item.get('preco_custo')
                preco_venda = item.get('preco_venda')
                
                updated_fields = []
                
                # Custo: usar preco_custo se existir, senao valor_unitario
                if preco_custo:
                    product.cost_price = float(preco_custo)
                elif valor_unitario:
                    product.cost_price = float(valor_unitario)
                updated_fields.append('cost_price')
                
                # Venda: usar preco_venda se existir, senao manter atual
                if preco_venda:
                    product.selling_price = float(preco_venda)
                    updated_fields.append('selling_price')
                
                if brand and product_ids[i].get('created'):
                    updated_fields.append('brand')
                
                # Apolar consignacao para produtos novos
                if consignment_mode and product_ids[i].get('created'):
                    product.stock_type = 'consignado'
                    product.consignment_supplier = supplier
                    if consignment_return_date:
                        product.consignment_return_date = consignment_return_date
                    updated_fields.extend(['stock_type', 'consignment_supplier', 'consignment_return_date'])
                
                product.save(update_fields=updated_fields)
                
                models.Inflow.objects.create(
                    supplier=supplier,
                    product=product,
                    quantity=int(quantity),
                    description=f'Entrada via NFe - {item.get("descricao", "")}',
                )
                created_count += 1
            except Product.DoesNotExist:
                errors.append(f'Produto ID {product_id} nao encontrado.')
            except Exception as e:
                errors.append(f'Erro ao criar entrada: {str(e)}')
        
        # Limpar sessao
        for key in ['xml_items', 'xml_emitente', 'supplier_id', 'supplier_created', 'product_ids', 'is_consignment_supplier']:
            request.session.pop(key, None)
        
        # Mensagens de resultado
        if created_count > 0:
            msg = f'{created_count} entrada(s) criada(s) com sucesso!'
            if consignment_mode:
                msg += ' Estoque consignado registrado.'
            else:
                msg += ' Estoque atualizado automaticamente.'
            messages.success(request, msg)
        
        if errors:
            for error in errors:
                messages.warning(request, error)
        
        return redirect('inflow_list')


class InflowCreateListAPIView(generics.ListCreateAPIView):
    queryset = models.Inflow.objects.all()
    serializer_class = serializers.InflowSerializer


class InflowRetrieveAPIView(generics.RetrieveAPIView):
    queryset = models.Inflow.objects.all()
    serializer_class = serializers.InflowSerializer
