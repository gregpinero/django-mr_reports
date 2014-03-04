//Simple script to put in edit links for existing parameters
//TODO: Later handle changing or adding new parameters
django.jQuery(document).ready(
    function (){
        django.jQuery('tr.dynamic-datasetparameter_set select').each(
            function (i,el){
                var parm_id = django.jQuery(el).val();
                var edit_url = '../../parameter/' + parm_id + '/';
                django.jQuery(el).parent().append('<a href="' + edit_url + '">Edit</a>');
            }
        );
    }
);

