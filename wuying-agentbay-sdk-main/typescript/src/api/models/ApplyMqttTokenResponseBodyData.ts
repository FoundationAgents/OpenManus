// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


/**
 */
export class ApplyMqttTokenResponseBodyData extends $dara.Model {
  accessKeyId?: string;
  clientId?: string;
  expiration?: string;
  instanceId?: string;
  regionId?: string;
  securityToken?: string;
  static names(): { [key: string]: string } {
    return {
      accessKeyId: 'AccessKeyId',
      clientId: 'ClientId',
      expiration: 'Expiration',
      instanceId: 'InstanceId',
      regionId: 'RegionId',
      securityToken: 'SecurityToken',
    };
  }

  static types(): { [key: string]: any } {
    return {
      accessKeyId: 'string',
      clientId: 'string',
      expiration: 'string',
      instanceId: 'string',
      regionId: 'string',
      securityToken: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

