from jobboard.apps.core.renderers import JobBoardJSONRenderer


class ProfileJSONRenderer(JobBoardJSONRenderer):
    object_label = "profile"
    pagination_object_label = "profiles"
    pagination_count_label = "profilesCount"
