#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>

# Tools to control and animate textures, switching images

import bpy # pylint: disable=import-error
import bpy.utils.previews # pylint: disable=import-error
from bpy.app.handlers import persistent # pylint: disable=import-error
import re
from .dublf import (
    DUBLF_fs,
    DUBLF_handlers,
    DuBLF_bl_ui,
    )
from .dublf.rigging import (
    DUBLF_rigging,
)

# ===================================================
# methods to update images on frame change and update
# ===================================================

def update_image(node):
    numImages = len(node.duik_texanim_images)
    if numImages > 0:
        index = node.duik_texanim_current_index
        if index < 0:
            index = 0
            node.duik_texanim_current_index = index
            return
        elif index >= numImages:
            index = numImages - 1
            node.duik_texanim_current_index = index
            return
        node.image = node.duik_texanim_images[index].image

def update_current_image( node, context ):
    """Changes the image used in the Texture Image node"""
    update_image(node)

@persistent
def update_image_handler( scene ):
    """Updates all TexAnim_images, as the update function does not work on playback"""
    # get all texanims in the scene
    for material in bpy.data.materials:
        if material.node_tree is not None:
            for node in material.node_tree.nodes:
                if node.bl_idname == 'ShaderNodeTexImage':
                    update_image(node)
    for nodeGroup in bpy.data.node_groups:
        for node in nodeGroup.nodes:
            if node.bl_idname == 'ShaderNodeTexImage':
                update_image(node)

# UTILS

def has_texanim(context):
    return obj_has_texanim(context) or bone_has_texanim(context)

def obj_has_texanim(context):
    obj = context.active_object
    numControls = 0
    if not (obj is None):
        numControls += numControls + len(obj.duik_linked_texanims) + len(obj.duik_copied_texanims)
    return numControls != 0

def bone_has_texanim(context):
    bone = context.active_pose_bone
    numControls = 0
    if not (bone is None):
        numControls = numControls + len(bone.duik_linked_texanims) + len(bone.duik_copied_texanims)
    return numControls != 0

def has_texanim_node(context, node):
    obj = get_active_poseBone_or_object(context)
    if obj is not None:
        for c in obj.duik_linked_texanims:
            if c.nodeTree is node.id_data and c.node == node.name:
                return True
        for c in obj.duik_copied_texanims:
            link = c.linked_node
            if link.nodeTree is node.id_data and link.node == node.name:
                return True
    return False

def get_active_poseBone_or_object(context):
    obj = context.active_pose_bone
    if obj is None:
        obj = context.active_object
    return obj

def get_active_node(context):
    try:
        node = context.active_node
        return node
    except AttributeError:
        return None
    
def draw_texanims_lists(obj,layout):
    layout.label(text="Linked TexAnims:")
    layout.template_list("DUIK_UL_linked_texanim", "", obj, 'duik_linked_texanims', obj, 'duik_linked_texanims_current', rows=3)
    #box = layout.box()
    #box.prop( obj.duik_linked_texanims[obj.duik_linked_texanims_current], 'node', text = 'Node')
    layout.operator( "texanim.unlink_control" , text = "Remove").control_index = obj.duik_linked_texanims_current
    layout.label(text="Copied TexAnims:")
    layout.template_list("DUIK_UL_copied_texanim", "", obj, 'duik_copied_texanims', obj, 'duik_copied_texanims_current', rows=3)
    layout.operator( "texanim.remove_control" , text = "Remove").control_index = obj.duik_copied_texanims_current

# CLASSES

class DUIK_TexAnimLink( bpy.types.PropertyGroup ):
    """A texanim control on an object or a pose_bone"""
    nodeTree: bpy.props.PointerProperty( type = bpy.types.ShaderNodeTree )
    node: bpy.props.StringProperty( )

class DUIK_TexAnimMovedTo( bpy.types.PropertyGroup ):
    """The link to the object or bone this texanim has been moved to"""
    obj: bpy.props.PointerProperty( type=bpy.types.Object )
    bone: bpy.props.StringProperty( )

class DUIK_TexAnimImage( bpy.types.PropertyGroup ):
    """One Image in the TexAnim"""
    image: bpy.props.PointerProperty( type = bpy.types.Image )
    name: bpy.props.StringProperty( name="Image", default="Image")

class DUIK_TexAnimProperties( bpy.types.PropertyGroup ):
    linked_node: bpy.props.PointerProperty( type = DUIK_TexAnimLink )
    images: bpy.props.CollectionProperty( type = DUIK_TexAnimImage )
    name: bpy.props.StringProperty( default="Name" )

class DUIK_OT_new_texanim_images( bpy.types.Operator ):
    """Adds a new image to the texanim"""
    bl_idname = "texanim.new_texanim_images"
    bl_label = "New Image"
    bl_options = {'REGISTER','UNDO'}

    filepath: bpy.props.StringProperty(name="File Path", description="Filepath used for importing images", maxlen= 1024, default= "")
    files: bpy.props.CollectionProperty(name="Files", type=bpy.types.OperatorFileListElement)

    @classmethod
    def poll(cls, context):
        node = context.active_node
        if node is None:
            return False
        return node.bl_idname == 'ShaderNodeTexImage'

    def execute(self, context):
        node = context.active_node

        filepath = re.split(r"[\\/]+", self.filepath)
        filepath = "/".join(filepath[0:-1])

        print(filepath)
        
        # File open and add image
        for file in self.files:
            name = DUBLF_fs.get_fileBaseName(file)
            image = bpy.data.images.load( filepath + "/" + file.name, check_existing=True )
            texAnimImage = node.duik_texanim_images.add()
            texAnimImage.image = image
            texAnimImage.name = name
        
        DuBLF_bl_ui.redraw()

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

class DUIK_OT_remove_texanim_image( bpy.types.Operator ):
    """Removes the active Image"""
    bl_idname = "texanim.remove_texanim_image"
    bl_label = "Remove Image"
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        node = context.active_node
        if node is None:
            return False
        return node.bl_idname == 'ShaderNodeTexImage'

    DuBLF_bl_ui.redraw()

    def execute(self, context):
        node = context.active_node
        # remove all keyframes referencing this image
        # and adjust values of other keyframes to continue referencing the right images
        current_index = node.duik_texanim_current_index
        for action in bpy.data.actions:
            fcurves = action.fcurves
            for curve in fcurves:
                if curve.data_path == 'nodes[\"' + node.name + '\"].duik_texanim_current_index':
                    keyframes = curve.keyframe_points
                    i = len(keyframes) -1
                    while i >= 0:
                        keyframe = keyframes[i]
                        val = keyframe.co[1]
                        if val == current_index:
                            keyframes.remove(keyframe)
                        if val > current_index:
                            keyframe.co[1] = val-1
                        i = i-1

        # remove this image
        node.duik_texanim_images.remove(current_index)
        return {'FINISHED'}

class DUIK_OT_texanim_image_move( bpy.types.Operator ):
    """Moves the image up or down"""
    bl_idname = "texanim.image_move"
    bl_label = "Move Up"
    bl_options = {'REGISTER','UNDO'}

    up: bpy.props.BoolProperty(default = True)

    @classmethod
    def poll(cls, context):
        node = context.active_node
        if node is None:
            return False
        return node.bl_idname == 'ShaderNodeTexImage'

    def execute(self, context):
        node = context.active_node
        current_index = node.duik_texanim_current_index
        images = node.duik_texanim_images

        if self.up and current_index <= 0: return {'CANCELLED'}
        if not self.up and current_index >= len(images) - 1: return {'CANCELLED'}

        new_index = 0
        if self.up: new_index = current_index - 1
        else: new_index = current_index + 1

        # update keyframes values
        for action in bpy.data.actions:
            fcurves = action.fcurves
            for curve in fcurves:
                if curve.data_path == 'nodes[\"' + node.name + '\"].duik_texanim_current_index':
                    keyframes = curve.keyframe_points
                    for keyframe in keyframes:
                        if keyframe.co[1] == new_index: keyframe.co[1] = current_index
                        elif keyframe.co[1] == current_index: keyframe.co[1] = new_index

        images.move(current_index, new_index)
        node.duik_texanim_current_index = new_index

        return {'FINISHED'}

class DUIK_OT_texanim_link_control( bpy.types.Operator ):
    """Adds a copy of the list to be animated on the 3D View > UI > Item panel
       Displayed only with a specific object selected
    """
    bl_idname = "texanim.link_control"
    bl_label = "Link to active object/bone"
    bl_description = "Add a control in the 3D View > UI > Item panel for the active object or pose bone"
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        node = get_active_node(context)
        if node is None: return False
        if has_texanim_node(context, node): return False
        return node.bl_idname == 'ShaderNodeTexImage'

    def execute( self, context):
        obj = get_active_poseBone_or_object(context)
        node = context.active_node

        texanimControl = obj.duik_linked_texanims.add()
        texanimControl.nodeTree = node.id_data
        texanimControl.node = node.name

        # cleaning! remove any node not available anymore
        # check if everything still exists
        i = len(obj.duik_linked_texanims) - 1
        while i >= 0:
            control = obj.duik_linked_texanims[i]
            nodeTree = control.nodeTree
            try:
                test = nodeTree.nodes[control.node]
            except:
                obj.duik_linked_texanims.remove(i)
            i = i-1

        DuBLF_bl_ui.redraw()

        return {'FINISHED'}

class DUIK_OT_texanim_unlink_control( bpy.types.Operator ):
    """Removes the link of the list from the 3D View > UI > Item panel
    """
    bl_idname = "texanim.unlink_control"
    bl_label = "Unlink from active object/bone"
    bl_description = "Unlinks the control from the 3D View > UI > Item panel for the active object or pose bone"
    bl_options = {'REGISTER','UNDO'}

    control_index: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(self, context):
        obj = get_active_poseBone_or_object(context)
        if obj is None: return False
        return len(obj.duik_linked_texanims) > 0

    def execute( self, context):
        obj = get_active_poseBone_or_object(context)

        # If we don't know which one, get from active node
        if self.control_index < 0:
            # Check if already there 
            node = get_active_node(context)
            if node is None: return {'CANCELLED'}
            i = len(obj.duik_linked_texanims) - 1
            while i >= 0:
                control = obj.duik_linked_texanims[i]
                nodeTree = control.nodeTree
                try:
                    test = nodeTree.nodes[control.node]
                except:
                    obj.duik_linked_texanims.remove(i)
                if node.id_data is nodeTree and node.name == control.node:
                    obj.duik_linked_texanims.remove(i)
                i = i-1
        # if we know, just remove
        else:
            obj.duik_linked_texanims.remove(self.control_index)

        DuBLF_bl_ui.redraw()

        return {'FINISHED'}

class DUIK_OT_texanim_move_control( bpy.types.Operator ):
    """Moves the list to the selected object or pose bone
    """
    bl_idname = "texanim.move_control"
    bl_label = "Move to active object/bone"
    bl_description = "Moves the control to the active object or pose bone"
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        node = get_active_node(context)
        if node is None: return False
        if has_texanim_node(context, node): return False
        return node.bl_idname == 'ShaderNodeTexImage'

    def execute(self, context):
        obj = get_active_poseBone_or_object(context)
        node = get_active_node(context)

        texanim_properties = obj.duik_copied_texanims.add()
        texanim_properties.name = node.duik_texanim_name
        texanim_properties.linked_node.nodeTree = node.id_data
        texanim_properties.linked_node.node = node.name

        # Copy images
        for image in node.duik_texanim_images:
            new_image = texanim_properties.images.add()
            new_image = image.image
            new_image.name = image.name

        # Remove them
        node.duik_texanim_images.clear()

        # Set the link
        if isinstance(obj, bpy.types.PoseBone):
            node.duik_texanim_moved_to.obj = obj.id_data
            node.duik_texanim_moved_to.bone = obj.name
        else:
            node.duik_texanim_moved_to.obj = obj.id_data
            node.duik_texanim_moved_to.bone = ''

        # Create index
        i = len(obj.duik_copied_texanims) -1
        if i == 0:
            obj.texanim_0 = bpy.props.IntProperty(default=0)

        # TODO Transfer keyframes

        DuBLF_bl_ui.redraw()

        return {'FINISHED'}

class DUIK_OT_texanim_remove_control( bpy.types.Operator ):
    """Removes the copy of the list from the active object or pose bone
    """
    bl_idname = "texanim.remove_control"
    bl_label = "Remove from active object/bone"
    bl_description = "Removes the control from the active object or pose bone"
    bl_options = {'REGISTER','UNDO'}

    control_index: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        obj = get_active_poseBone_or_object(context)
        if obj is None: return False
        return len(obj.duik_copied_texanims) > 0

    def execute(self, context):
        obj = get_active_poseBone_or_object(context)
        remove_index = self.control_index
        remove_texanim = None
        # If we don't know which one, get from active node
        if self.control_index < 0:
            # Check if already there 
            node = get_active_node(context)
            if node is None: return {'CANCELLED'}
            i = len(obj.duik_copied_texanims) - 1
            while i >= 0:
                control = obj.duik_copied_texanims[i]
                nodeTree = control.linked_node.nodeTree
                nodeName = control.linked_node.node
                if node.id_data is nodeTree and node.name == nodeName:
                    remove_index = i
                    remove_texanim = control
                    break
                i = i-1
        # if we know, just get it
        else:
            remove_texanim = obj.duik_copied_texanims[remove_index]

        if remove_texanim is None: return {'CANCELLED'}

        # copy everything back to the current texanim
        node_tree = remove_texanim.linked_node.nodeTree
        try:
            node = node_tree.nodes[remove_texanim.linked_node.node]
        except:
            node = None

        if node is None:
            obj.duik_copied_texanims.remove(remove_index)
            return {'FINISHED'}

        for image in remove_texanim.images:
            new_image = node.duik_texanim_images.add()
            new_image.image = image.image
            new_image.name = image.name

        # Remove Link
        node.duik_texanim_moved_to.obj = None
        node.duik_texanim_moved_to.bone = ''

        # TODO Transfer keyframes


        # Remove
        obj.duik_copied_texanims.remove(remove_index)

        DuBLF_bl_ui.redraw()

        return {'FINISHED'}

class DUIK_UL_texanim( bpy.types.UIList ):
    """The list of images in the UI"""
    bl_idname = "DUIK_UL_texanim"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        layout.prop(item, "name", text="", emboss=False, icon = 'FILE_IMAGE')

class DUIK_UL_linked_texanim( bpy.types.UIList ):
    """The list of linked texanims on an object"""
    bl_idename = "DUIK_UL_linked_texanim"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        # get the texanim
        nodeTree = item.nodeTree
        node = item.node
        try:
            texanim = nodeTree.nodes[node]
            layout.prop(texanim, "duik_texanim_name", text="", emboss=False)
        except:
            layout.label(text='Broken Link')

class DUIK_UL_copied_texanim( bpy.types.UIList ):
    """The List of copied texanims on an object"""
    bl_idname = "DUIK_UL_copied_texanim"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        layout.prop(item, "name", text="", emboss=False)

class DUIK_PT_texanim_ui( bpy.types.Panel ):
    """The panel for managing the images (adding, removing, etc)"""
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_label = "Duik TexAnim"
    bl_idname = "DUIK_PT_texanim_ui"
    bl_category = 'Item'

    @classmethod
    def poll(cls, context):
        node = context.active_node
        if node is None:
            return False
        return node.bl_idname == 'ShaderNodeTexImage'

    def draw( self, context ):
        layout = self.layout

        node = context.active_node

        layout.prop( node, 'duik_texanim_name', text = "Name")

        # Check if it has been moved to an object/bone
        moved_obj = node.duik_texanim_moved_to.obj
        if moved_obj is not None:
            layout.label(text="This TexAnim has been moved to: " + moved_obj.name)
            bone = node.duik_texanim_moved_to.bone
            if bone != '':
                layout.label(text="Bone: " + bone.name)
            return

        row = layout.row()

        # template_list now takes two new args.
        # The first one is the identifier of the registered UIList to use (if you want only the default list,
        # with no custom draw code, use "UI_UL_list").
        row.template_list("DUIK_UL_texanim", "", node, "duik_texanim_images", node, "duik_texanim_current_index" , rows = 3 )

        col = row.column(align=True)
        col.operator("texanim.new_texanim_images", icon='ADD', text="")
        col.operator("texanim.remove_texanim_image", icon='REMOVE', text="")

        col.separator()
        col.operator("texanim.image_move", icon='TRIA_UP', text="").up = True
        col.operator("texanim.image_move", icon='TRIA_DOWN', text="").up = False

        layout.prop( node, 'duik_texanim_current_index', text = "Current Image" )

        layout.separator()

        row = layout.split(factor=.9, align=True)
        row.operator( "texanim.link_control" )
        row.operator( "texanim.unlink_control", icon='X', text='' )
        row = layout.split(factor=.9, align=True)
        row.operator( "texanim.move_control" )
        row.operator( "texanim.remove_control",  icon='X', text='' )

class DUIK_PT_texanim_control( bpy.types.Panel ):
    """The list as a control in the 3D View > UI > Item panel"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Duik TexAnim"
    bl_idname = "DUIK_PT_texanim_control"
    bl_category = 'Item'

    @classmethod
    def poll(cls, context):
        return has_texanim(context)

    def addLinkedList( self, layout, texanimControl ):
        # check if everything still exists
        nodeTree = texanimControl.nodeTree
        try:
            texanim = nodeTree.nodes[texanimControl.node]
            layout.label( text = texanim.duik_texanim_name + ":" )
            layout.template_list("DUIK_UL_texanim", "", texanim , "duik_texanim_images", texanim , "duik_texanim_current_index" , rows = 3 )
        except:
            return False

        return True

    def addCopiedList( self, layout, texanimControl, obj, index ):
        layout.label( text = texanimControl.name )
        # get index
        layout.template_list("DUIK_UL_texanim", "", texanimControl , "images", obj , "texanim_" + str(index), rows = 3 )

    def addControls( self, obj, layout ):
        if obj is None:
            return
        controls = obj.duik_linked_texanims
        for control in controls:
            self.addLinkedList( layout, control )
        controls = obj.duik_copied_texanims
        for i, control in enumerate(controls):
            self.addCopiedList( layout, control, obj, i )

    def draw( self, context ):
        layout = self.layout

        self.addControls( context.active_pose_bone, layout )
        self.addControls( context.active_object, layout )

class DUIK_PT_texanim_object_settings( bpy.types.Panel ):
    bl_label = "Duik TexAnim"
    bl_idname = "DUIK_PT_texanim_object_settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return obj_has_texanim(context)

    def draw(self, context):
        obj = context.active_object
        draw_texanims_lists(obj, self.layout)
        
class DUIK_PT_texanim_bone_settings( bpy.types.Panel ):
    bl_label = "Duik TexAnim"
    bl_idname = "DUIK_PT_texanim_bone_settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "bone"

    @classmethod
    def poll(cls, context):
        return bone_has_texanim(context)

    def draw(self, context):
        bone = context.active_pose_bone
        draw_texanims_lists(bone, self.layout)

classes = (
    DUIK_TexAnimLink,
    DUIK_TexAnimMovedTo,
    DUIK_TexAnimImage,
    DUIK_TexAnimProperties,
    DUIK_OT_new_texanim_images,
    DUIK_OT_remove_texanim_image,
    DUIK_OT_texanim_image_move,
    DUIK_OT_texanim_link_control,
    DUIK_OT_texanim_unlink_control,
    DUIK_OT_texanim_move_control,
    DUIK_OT_texanim_remove_control,
    DUIK_UL_texanim,
    DUIK_UL_linked_texanim,
    DUIK_UL_copied_texanim,
    DUIK_PT_texanim_ui,
    DUIK_PT_texanim_control,
    DUIK_PT_texanim_object_settings,
    DUIK_PT_texanim_bone_settings,
)

def register():
    # register
    for cls in classes:
        bpy.utils.register_class(cls)

    # Add images on ShaderNodeTexImage
    if not hasattr( bpy.types.ShaderNodeTexImage, 'duik_texanim_images' ):
        bpy.types.ShaderNodeTexImage.duik_texanim_images = bpy.props.CollectionProperty( type = DUIK_TexAnimImage, options={'LIBRARY_EDITABLE'} )
    if not hasattr( bpy.types.ShaderNodeTexImage, 'duik_texanim_current_index' ):
        bpy.types.ShaderNodeTexImage.duik_texanim_current_index = bpy.props.IntProperty( update=update_current_image,  options={'ANIMATABLE','LIBRARY_EDITABLE'} )
    if not hasattr( bpy.types.ShaderNodeTexImage, 'duik_texanim_name' ):
        bpy.types.ShaderNodeTexImage.duik_texanim_name = bpy.props.StringProperty( default="Name" )
    if not hasattr( bpy.types.ShaderNodeTexImage, 'duik_texanim_moved_to' ):
        bpy.types.ShaderNodeTexImage.duik_texanim_moved_to = bpy.props.PointerProperty( type=DUIK_TexAnimMovedTo )


    # Add controls on pose bones and objects
    if not hasattr( bpy.types.Object, 'duik_linked_texanims' ):
        bpy.types.Object.duik_linked_texanims = bpy.props.CollectionProperty( type = DUIK_TexAnimLink )
    if not hasattr( bpy.types.Object, 'duik_linked_texanims_current' ):
        bpy.types.Object.duik_linked_texanims_current = bpy.props.IntProperty( )
    if not hasattr( bpy.types.Object, 'duik_copied_texanims' ):
        bpy.types.Object.duik_copied_texanims = bpy.props.CollectionProperty( type = DUIK_TexAnimProperties )
    if not hasattr( bpy.types.Object, 'duik_copied_texanims_current' ):
        bpy.types.Object.duik_copied_texanims_current = bpy.props.IntProperty( )
    if not hasattr( bpy.types.PoseBone, 'duik_linked_texanims' ):
        bpy.types.PoseBone.duik_linked_texanims = bpy.props.CollectionProperty( type = DUIK_TexAnimLink )
    if not hasattr( bpy.types.PoseBone, 'duik_linked_texanims_current' ):
        bpy.types.PoseBone.duik_linked_texanims_current = bpy.props.IntProperty( )
    if not hasattr( bpy.types.PoseBone, 'duik_copied_texanims' ):
        bpy.types.PoseBone.duik_copied_texanims = bpy.props.CollectionProperty( type = DUIK_TexAnimProperties )
    if not hasattr( bpy.types.PoseBone, 'duik_copied_texanims_current' ):
        bpy.types.PoseBone.duik_copied_texanims_current = bpy.props.IntProperty( )

    # Add handler
    DUBLF_handlers.frame_change_post_append( update_image_handler )

def unregister():
    # Remove handler
    DUBLF_handlers.frame_change_post_remove( update_image_handler )

    del bpy.types.ShaderNodeTexImage.duik_texanim_images
    del bpy.types.ShaderNodeTexImage.duik_texanim_current_index
    del bpy.types.Object.duik_linked_texanims
    del bpy.types.PoseBone.duik_linked_texanims

    # unregister
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
