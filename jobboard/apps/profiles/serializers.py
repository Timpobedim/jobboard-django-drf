from rest_framework import serializers

from jobboard.apps.profiles.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    bio = serializers.CharField(allow_blank=True, required=False)
    image = serializers.SerializerMethodField()
    isCompany = serializers.BooleanField(source="is_company", read_only=True)
    companyName = serializers.CharField(source="company_name", read_only=True)
    following = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ("username", "bio", "image", "isCompany", "companyName", "following")

    def get_image(self, obj: Profile) -> str | None:
        return obj.image or None

    def get_following(self, instance: Profile) -> bool:
        # Флаг проставляется во вьюхах из аннотации запроса — без отдельного SQL на каждый профиль.
        annotated = getattr(instance, "is_followed", None)
        if annotated is not None:
            return bool(annotated)

        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False

        return bool(request.user.profile.is_following(instance))
