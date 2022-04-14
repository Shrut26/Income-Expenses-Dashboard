from locale import currency
from math import fabs
from unicodedata import category
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .models import Category, Expense
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import User
import json
from django.http import JsonResponse, HttpResponse
from userpreferences.models import Userpreference
import datetime
import csv
import xlwt

# Create your views here.

def search_expenses(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        expenses = Expense.objects.filter(
            amount__istartswith = search_str , owner = request.user) | Expense.objects.filter(
            date__istartswith = search_str , owner = request.user) | Expense.objects.filter(
            description__icontains = search_str , owner = request.user)| Expense.objects.filter(
            category__icontains = search_str , owner = request.user)
        
        data = expenses.values()
        return JsonResponse(list(data) , safe = False)


@login_required(login_url='/authentication/login')
def index(request):
    Categories = Category.objects.all()   #taking all the categoies from backend
    expenses = Expense.objects.filter(owner=request.user) #filtering all the expenses according to date of expense
    paginator = Paginator(expenses,5) # paginating all expenses
    page_number = request.GET.get('page')  # writing page number below
    page_obj = Paginator.get_page(paginator,page_number) 
    # currency = Userpreference.objects.get(user=request.user).currency
    currency = Userpreference.objects.get(user=request.user).currency  # getting currency from userpreferences module
    context = {
        'expenses' : expenses,
        'page_obj' : page_obj,
        'currency' : currency,
    }
    return render(request,'expenses/index.html',context)
 
def add_expense(request):
    Categories = Category.objects.all() #getting categories
    
    context = {
            'Categories' : Categories,
            'values': request.POST
        }
    if request.method == 'GET':
        
        return render(request,'expenses/add_expense.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']  #taking amount
        
        if not amount:  #  test case -> if amount not there show error 
            messages.error(request,'Amount is required')  
            return render(request,'expenses/add_expense.html', context)

    
        description = request.POST['description'] # taking description
        category = request.POST['category'] #taking category
        date = request.POST['expense_date'] #taking date

        if not description:#  test case -> if description not there show error 
            messages.error(request,'Description is required')  
            return render(request,'expenses/add_expense.html', context)

        if not date:#  test case -> if date not there show error 
            messages.error(request,'Date is required')  
            return render(request,'expenses/add_expense.html', context)

        Expense.objects.create(owner= request.user, amount = amount, description = description, category = category, date = date)
        messages.success(request,'Expense added')
        return redirect('expenses')

#editing expenses: using same logic as explained above
def expense_edit(request,id):
    expense = Expense.objects.get(pk=id)
    Categories = Category.objects.all()
    context = {
        'expense' : expense,
        'values' : expense,
        'Categories' : Categories
    }
    if request.method == 'GET':
        return render(request,'expenses/edit_expense.html',context)
    if request.method == 'POST':
        amount = request.POST['amount']
        
        if not amount:
            messages.error(request,'Amount is required')  
            return render(request,'expenses/edit_expense.html', context)

    
        description = request.POST['description']
        category = request.POST['category']
        date = request.POST['expense_date']

        if not description:
            messages.error(request,'Description is required')  
            return render(request,'expenses/edit_expense.html', context)

        if not date:
            messages.error(request,'Date is required')  
            return render(request,'expenses/edit_expense.html', context)
        #changing inputs
        Expense.objects.create(owner= request.user, amount = amount, description = description, category = category, date = date)
        expense.owner = request.user
        expense.amount = amount
        expense.description = description
        expense.category = category
        expense.date = date 
        expense.save() #saving the changes done
        messages.success(request,'Expense Updated')
        return redirect('expenses')
        messages.info(request,'Handling post form')
        return render(request,'expenses/edit_expense.html',context)

#deleting the expenses
def delete_expense(request,id):
    expense = Expense.objects.get(pk=id)
    expense.delete()
    messages.success(request,'Expense removed')
    return redirect('expenses')

#plotting of distribution
def expense_category_summary(request):
    todays_date = datetime.date.today()  #today's date
    six_months_ago = todays_date - datetime.timedelta(days = 30*6) #date before six months
    expenses = Expense.objects.filter(owner = request.user,date__gte = six_months_ago, date__lte = todays_date)
    finalrep = {}
    
    def get_category(expense):
        return expense.category
        
    category_lists = list(set(map(get_category, expenses)))      #preparing the list for the same
    

    def get_expense_category_amount(category):
        amount = 0
        filtered_by_category = expenses.filter(category = category)

        for item in filtered_by_category:
            amount = amount + item.amount                      #adding up amount as filtered

        return amount


    for x in expenses:
        for y in category_lists:
            finalrep[y] = get_expense_category_amount(y)


    return JsonResponse({'expense_category_data' : finalrep}, safe = False)


#to show the stats/ distribution web page
def stats_view(request):
    return render(request,'expenses/stats.html')


#module to export_csv 
def export_csv(request):

    response = HttpResponse(content_type = 'text/csv')  #getting of the http response
    response['Content-Disposition'] = 'attachment; filename = Expenses' + \
               str(datetime.datetime.now())+'.csv'  #generating file name
    
    writer = csv.writer(response)   #creating an object to write csv
    writer.writerow(['Amount', 'Description', 'Category', 'Date'])   #header of the csv file

    expenses  = Expense.objects.filter(owner = request.user)  #getting all the expenses

    for expense in expenses:
        writer.writerow([expense.amount, expense.description, expense.category, expense.date])  #writing all the expenses


    return response

#exporting to excel
def export_excel(request):
    response = HttpResponse(content_type = 'application/ms-excel')  #getting HTTP response
    response['Content-Disposition'] = 'attachment; filename = Expenses' + \
               str(datetime.datetime.now())+'.xls' #file naming
    
    wb = xlwt.Workbook(encoding='utf-8') #setting up workbook
    ws = wb.add_sheet('Expenses') #adding sheet to workbord
    row_num = 0 #initialising row number
    font_style = xlwt.XFStyle()  #font style 
    font_style.font.bold = True # making font style of head row as bold

    columns = ['Amount', 'Description', 'Category', 'Date'] # adding up headers

    for col_num in range(len(columns)):
        ws.write(row_num,col_num, columns[col_num], font_style) #adding cells

    font_style = xlwt.XFStyle() #font of data

    rows = Expense.objects.filter(owner = request.user).values_list('amount', 'description','category','date') #getting all the data in rows

    for row in rows:
        row_num+=1

        for col_num in range(len(row)): #writing row data
            ws.write(row_num,col_num, str(row[col_num]), font_style)

    wb.save(response) #saving workbook
    return response



    
