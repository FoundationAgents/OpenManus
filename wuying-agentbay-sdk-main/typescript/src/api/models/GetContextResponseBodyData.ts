// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class GetContextResponseBodyData extends $dara.Model {
  createTime?: string;
  id?: string;
  lastUsedTime?: string;
  name?: string;
  osType?: string;
  state?: string;
  static names(): { [key: string]: string } {
    return {
      createTime: 'CreateTime',
      id: 'Id',
      lastUsedTime: 'LastUsedTime',
      name: 'Name',
      osType: 'OsType',
      state: 'State',
    };
  }

  static types(): { [key: string]: any } {
    return {
      createTime: 'string',
      id: 'string',
      lastUsedTime: 'string',
      name: 'string',
      osType: 'string',
      state: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

