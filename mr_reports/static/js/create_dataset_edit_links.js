//Simple script to put in edit links for existing datasets
//TODO: Later handle changing or adding new datasets
django.jQuery(document).ready(
    function (){
        django.jQuery('tr.dynamic-reportdataset_set select').each(
            function (i,el){
                var parm_id = django.jQuery(el).val();
                var edit_url = '../../dataset/' + parm_id + '/';
                django.jQuery(el).parent().append('<a href="' + edit_url + '">Edit</a>');
            }
        );
    }
);

