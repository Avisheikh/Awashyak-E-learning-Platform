from django.shortcuts import render
from .models import Course, Module, Content
from django.urls import reverse_lazy
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Course
from .forms import ModuleFormSet
from django.shortcuts import redirect, get_object_or_404
from django.views.generic.base import TemplateResponseMixin, View
from django.forms.models import modelform_factory
from django.apps import apps 
from django.contrib.auth.models import User

# Create your views here.

def renderCoursePage(request):
    return render(request,'coursePage.html')


# Need to provide a specific behaviour for several class-based
# views so use mixins (it is not compulsory)
# Using mixins to create, read, update, delete courses

#Used for views that interact with any model that contains an owner attribute
class OwnerMixin(object):
    
    #Get the base QuerySet
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner = self.request.user)

#ownerEditMixin views with forms or model forms
class OwnerEditMixin(object):
    def form_valid(self,form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


#ownerMixin inherits LofinRequiredMixin and PermissionRequiredMixin Because
# 1. LoginRequiredMixin replicates the login_required decoratores functionality and
# 2. PermissionRequiredMixin grants access to view to users with a specific permission.
class OwnerCourseMixin(OwnerMixin):
    model = Course
    fields = ['subject','title','slug','overview']
    #  Redirect the user after the form is successfully submitted or deleted
    success_url = reverse_lazy('manage_course_list')

class OwnerCourseEditMixi(OwnerCourseMixin, OwnerEditMixin):
    template_name = 'courses/manage/course/form.html'
  
   
#List the courses created by the user
class ManageCourseListView(OwnerCourseMixin, ListView):


    template_name = 'courses/manage/course/list.html'

   
#Uses a model form to create a new course object
class CourseCreateView(OwnerCourseEditMixi,CreateView):
   pass
#Allows the editing of an existing course object
class CourseUpdateView(OwnerCourseEditMixi, UpdateView):
   pass


#Confirm to course deletion
class CourseDeleteView(OwnerCourseMixin, DeleteView):
    template_name = 'courses/manage/course/delete.html'
  
# CourseModuleUpdateView handles the formset to add , update and delete modules for a specific course.
# TemplateResponseMixin rende templates and retun a HTTP response.
class CourseModuleUpdateView(TemplateResponseMixin,View):
    template_name = 'courses/manage/module/formset.html'
    course = None

    # get_formset avoid repating the code to build the fromset.
    def get_formset(self,data = None):
        return ModuleFormSet(instance = self.course, data = data)

    # dispatch takes an HTTP request and its parameter to match the HTTP method used.
    def dispatch(self, request, pk):
        self.course = get_object_or_404(Course, id = pk, owner = request.user)

        return super().dispatch(request,pk)

    # Executed for GET requests.
    def get(self,request,*args,**kwargs):
        formset = self.get_formset()
        # render_to_response render to the template
        return self.render_to_response(
            {'course': self.course, 'formset':formset}
        )

    # Executed for POST requests
    def post(self,request, *args, **kwargs):
        formset = self.get_formset(data = request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('manage_course_list')
        return self.render_to_response(
            {'course':self.course,'formset':formset}
        )

# ContentCreateUpdateView help to create and update different models' contents.
class ContentCreateUpdateView(TemplateResponseMixin,View):
    module = None
    model = None
    obj = None
    template_name = 'courses/manage/content/form.html'

    #Check that the given model name is one of the four content models
    def get_model(self,model_name):
        if model_name in ['text','video','image','file']:
                
            # apps module help to obtain the actual class for the give model name.
            return apps.get_model(app_label = 'courseManagementSystem',model_name = model_name)

        return None

    # get_form helps to exclude specify common fileds from the form and let all other attribute be included automativally.
    def get_form(self,model,*args,**kwargs):
        Form = modelform_factory(model, exclude=['owner','enroll','created','updated']) 

        return Form(*args, **kwargs)

    # dispatch receives URL parameters and stor the corresponding module, model and content object as class attribute.
    def dispatch(self, request, module_id, model_name, id = None):
        self.module = get_object_or_404(Module, id = module_id, course__owner= request.user)

        self.model = self.get_model(model_name)

        if id:
            self.obj = get_object_or_404(self.model,id = id, owner = request.user)
        return super().dispatch(request, module_id,model_name,id)

    # Excuted when a GET request is received
    def get(self, request,module_id,model_name, id = None):
        form = self.get_form(self.model, instance = self.obj)
        return self.render_to_response({'form':form,'object':self.obj})

    # Excuted when a POST request is received
    def post(self, request,module_id, model_name, id = None):
        form = self.get_form(self.model, instance = self.obj, data = request.POST, files = request.FILES)

        if form.is_valid():
            obj = form.save(commit = False)
            obj.owner = request.user
            obj.save()

            if not id:
                #new content
                Content.objects.create(module = self.module, item = obj)

            return redirect('module_content_list', self.module.id)
            
        return self.render_to_response({'form': form, 'object': self.obj})

# ContentDeleteView deletes the content object and redirects the user to the module_content_list URL
class ContentDeleteView(View):

    def post(self,request,id):
        content = get_object_or_404(Content, id = id , module__course__owner = request.user)
        module = content.module
        content.item.delete()
        content.delete()
        return redirect('module_content_list',module.id)


# ModuleContentListView gets the module object with the given id that belongs to current user 
# Renders a template with the give module
class ModuleContentListView(TemplateResponseMixin,View):
    template_name = 'courses/manage/module/content_list.html'

    def get(self,request,module_id):
        module = get_object_or_404(Module, id = module_id, course__owner = request.user)
        return self.render_to_response({'module': module})
