from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Blog, BlogCategory
from .forms import BlogForm, CommentForm

def blog_list(request):
    category_name = request.GET.get('category', 'all').lower()
    categories = BlogCategory.objects.all()
    if category_name == 'all':
        blogs = Blog.objects.all()
    else:
        blogs = Blog.objects.filter(category__name__iexact=category_name)
    context = {
        'blogs': blogs,
        'categories': categories,
        'selected_category': category_name,
    }
    return render(request, 'blog/blog_list.html', context)

def blog_detail(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    comments = blog.comments.all()
    if request.method == 'POST':
        form = CommentForm(request.POST, user=request.user)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.blog = blog
            if request.user.is_authenticated:
                comment.user = request.user
            else:
                comment.name = form.cleaned_data['name']
            comment.save()
            return redirect('blog:blog_detail', blog_id=blog_id)
    else:
        form = CommentForm(user=request.user)
    context = {
        'blog': blog,
        'comments': comments,
        'form': form,
    }
    return render(request, 'blog/blog_detail.html', context)

@login_required(login_url='accounts:login_page')
def create_blog(request):
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.author = request.user
            blog.save()
            messages.success(request, 'Blog created successfully!')
            return redirect('blog:blog_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BlogForm()
    return render(request, 'blog/blog_form.html', {'form': form})